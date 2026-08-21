"""
JARVIS Base Plugin Interface Module.

Defines the abstract base class and tool adapter bridge for custom plugins in JARVIS.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from plugins.permissions import PluginPermission
from plugins.schemas import PluginMetadata, PluginStatus
from tools.base import BaseTool

logger = logging.getLogger(__name__)


class PluginToolBridge(BaseTool):
    """
    Adapter that exposes a Plugin action/method as a BaseTool for the ToolRegistry.
    """

    def __init__(
        self,
        plugin: "BasePlugin",
        tool_name: str,
        description: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initializes the plugin tool bridge adapter.

        Args:
            plugin: Target BasePlugin instance.
            tool_name: Name of tool exposed to ToolRegistry.
            description: Tool description for LLM prompts.
            parameters: Parameter schema dictionary.
        """
        self._plugin = plugin
        self._tool_name = tool_name
        self._description = description
        self._parameters = parameters or {}

    @property
    def name(self) -> str:
        return self._tool_name

    @property
    def description(self) -> str:
        return self._description

    @property
    def parameters(self) -> Dict[str, Any]:
        return self._parameters

    async def execute(self, **kwargs: Any) -> Any:
        return await self._plugin.execute_tool(self._tool_name, **kwargs)


class BasePlugin(ABC):
    """
    Abstract Base Class for custom plugins.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initializes the plugin with optional configuration dictionary.

        Args:
            config: Optional plugin settings dictionary.
        """
        self.config: Dict[str, Any] = config or {}
        self._enabled: bool = True
        self._last_error: Optional[str] = None
        self._execution_count: int = 0

    @property
    @abstractmethod
    def metadata(self) -> PluginMetadata:
        """
        Returns the plugin metadata.

        Returns:
            PluginMetadata: Plugin specification.
        """
        pass

    @property
    def name(self) -> str:
        return self.metadata.name

    @property
    def version(self) -> str:
        return self.metadata.version

    @property
    def description(self) -> str:
        return self.metadata.description

    @property
    def permissions(self) -> List[PluginPermission]:
        return self.metadata.permissions

    @property
    def capabilities(self) -> List[str]:
        return self.metadata.capabilities

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def last_error(self) -> Optional[str]:
        return self._last_error

    @property
    def execution_count(self) -> int:
        return self._execution_count

    def get_status(self) -> PluginStatus:
        """
        Returns structured status information for dashboard and management APIs.

        Returns:
            PluginStatus: Status model instance.
        """
        return PluginStatus(
            name=self.name,
            version=self.version,
            description=self.description,
            enabled=self._enabled,
            permissions=[
                p.value if isinstance(p, PluginPermission) else str(p)
                for p in self.permissions
            ],
            capabilities=self.capabilities,
            last_error=self._last_error,
            execution_count=self._execution_count,
        )

    async def initialize(self) -> None:
        """
        Lifecycle hook called when plugin is loaded.
        """
        pass

    async def shutdown(self) -> None:
        """
        Lifecycle hook called when plugin is unloaded or assistant shuts down.
        """
        pass

    def get_tools(self) -> List[BaseTool]:
        """
        Returns a list of BaseTool adapters to bridge plugin capabilities to ToolRegistry.

        Returns:
            List[BaseTool]: Bridged tool instances.
        """
        return []

    @abstractmethod
    async def execute(self, capability: str, **kwargs: Any) -> Any:
        """
        Asynchronously executes a capability/action on the plugin.

        Args:
            capability: Requested capability or method name.
            **kwargs: Arguments passed to capability.

        Returns:
            Any: Result of plugin execution.
        """
        pass

    async def execute_tool(self, tool_name: str, **kwargs: Any) -> Any:
        """
        Executes a bridged tool call, tracking execution metrics and isolating errors.

        Args:
            tool_name: Bridged tool name.
            **kwargs: Arguments passed to execution.

        Returns:
            Any: Result of plugin capability execution.
        """
        if not self._enabled:
            raise RuntimeError(f"Plugin '{self.name}' is currently disabled.")

        self._execution_count += 1
        try:
            result = await self.execute(capability=tool_name, **kwargs)
            self._last_error = None
            return result
        except Exception as e:
            self._last_error = str(e)
            logger.error(
                "Plugin '%s' execution error in capability/tool '%s': %s",
                self.name,
                tool_name,
                e,
            )
            raise
