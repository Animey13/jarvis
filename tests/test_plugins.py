"""
Unit and integration tests for Core Plugin Infrastructure.

Tests PluginPermission, BasePlugin, PluginRegistry, PluginManager,
tool bridging, dynamic discovery, enable/disable toggles, and failure isolation.
"""

import pytest
from typing import Any, Dict, List

from plugins.base import BasePlugin, PluginToolBridge
from plugins.manager import PluginManager
from plugins.permissions import PluginPermission
from plugins.registry import PluginRegistry
from plugins.schemas import PluginMetadata, PluginStatus
from tools.registry import ToolRegistry


class DummyPlugin(BasePlugin):
    """Simple test plugin."""

    def __init__(self, config: Dict[str, Any] = None) -> None:
        super().__init__(config=config)
        self.executed_count = 0

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="dummy",
            version="1.0.0",
            description="Test dummy plugin",
            capabilities=["echo", "echo_tool"],
            permissions=[PluginPermission.READ_ONLY],
        )

    def get_tools(self) -> List[Any]:
        return [
            PluginToolBridge(
                plugin=self,
                tool_name="echo_tool",
                description="Echoes back input message.",
                parameters={"msg": {"type": "string", "required": True}},
            )
        ]

    async def execute(self, capability: str, **kwargs: Any) -> Any:
        self.executed_count += 1
        cap = capability.lower().strip()
        if cap in ("echo", "echo_tool"):
            msg = kwargs.get("msg", "")
            if msg == "error":
                raise RuntimeError("Triggered error")
            return {"echo": msg}
        raise ValueError(f"Unknown capability {capability}")


class FaultyPlugin(BasePlugin):
    """Plugin that fails during initialization or execution."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="faulty",
            version="0.1.0",
            description="Plugin that raises exceptions",
            capabilities=["crash"],
            permissions=[PluginPermission.EXECUTION],
        )

    async def execute(self, capability: str, **kwargs: Any) -> Any:
        raise RuntimeError("Faulty plugin crashed on execution")


@pytest.mark.asyncio
async def test_plugin_permission_enum():
    assert PluginPermission.READ_ONLY.value == "read_only"
    assert PluginPermission.NETWORK.value == "network"
    assert PluginPermission.has_value("read_only") is True
    assert PluginPermission.has_value("invalid_perm") is False


@pytest.mark.asyncio
async def test_plugin_registry_operations():
    registry = PluginRegistry()
    plugin = DummyPlugin()

    # Registration
    registry.register(plugin)
    assert registry.get("dummy") is plugin
    assert len(registry.list()) == 1

    # Prevent duplicate registration
    with pytest.raises(ValueError, match="already registered"):
        registry.register(DummyPlugin())

    # Enable and Disable
    assert registry.disable("dummy") is True
    assert plugin.enabled is False
    assert registry.enable("dummy") is True
    assert plugin.enabled is True

    # Status summary
    statuses = registry.discover()
    assert len(statuses) == 1
    assert isinstance(statuses[0], PluginStatus)
    assert statuses[0].name == "dummy"

    # Unregister
    unregistered = registry.unregister("dummy")
    assert unregistered is plugin
    assert registry.get("dummy") is None


@pytest.mark.asyncio
async def test_plugin_tool_bridge_execution():
    tool_registry = ToolRegistry()
    plugin = DummyPlugin()
    tool_bridge = plugin.get_tools()[0]

    tool_registry.register_tool(tool_bridge)
    assert tool_registry.get_tool("echo_tool") is not None

    # Execute via ToolRegistry
    res = await tool_registry.execute_tool("echo_tool", msg="Hello World")
    assert res["status"] == "success"
    assert res["result"]["echo"] == "Hello World"
    assert plugin.execution_count == 1

    # Disable plugin and attempt execution
    plugin.enabled = False
    err_res = await tool_registry.execute_tool("echo_tool", msg="Test")
    assert err_res["status"] == "error"
    assert "disabled" in err_res["error"]


@pytest.mark.asyncio
async def test_plugin_manager_lifecycle_and_isolation():
    tool_registry = ToolRegistry()
    manager = PluginManager(tool_registry=tool_registry)

    dummy = DummyPlugin()
    faulty = FaultyPlugin()

    assert manager.register_plugin(dummy) is True
    assert manager.register_plugin(faulty) is True

    # Ensure tools bridged
    assert tool_registry.get_tool("echo_tool") is not None

    # Verify status discovery
    statuses = manager.get_plugin_statuses()
    assert len(statuses) >= 2

    # Disable faulty plugin
    assert manager.disable_plugin("faulty") is True
    assert faulty.enabled is False

    # Failure isolation test
    with pytest.raises(RuntimeError):
        await dummy.execute_tool("echo_tool", msg="error")

    # Dummy last_error populated
    assert dummy.last_error is not None
    assert "Triggered error" in dummy.last_error

    await manager.shutdown()
