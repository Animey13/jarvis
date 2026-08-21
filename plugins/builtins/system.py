"""
JARVIS System Plugin Module.

Bridges existing local system tools (get_current_datetime, calculator,
get_system_status, list_files, read_file, restricted_command) into the plugin framework.
"""

from typing import Any, Dict, List

from plugins.base import BasePlugin, PluginToolBridge
from plugins.permissions import PluginPermission
from plugins.schemas import PluginMetadata
from tools.base import BaseTool
from tools.system_tools import (
    CalculatorTool,
    DateTimeTool,
    ListFilesTool,
    ReadFileTool,
    RestrictedCommandTool,
    SystemStatusTool,
)


class SystemPlugin(BasePlugin):
    """
    Built-in plugin providing local system operations, diagnostics, and math calculations.
    """

    def __init__(self, config: Dict[str, Any] = None) -> None:
        super().__init__(config=config)
        self._dt_tool = DateTimeTool()
        self._calc_tool = CalculatorTool()
        self._status_tool = SystemStatusTool()
        self._list_tool = ListFilesTool()
        self._read_tool = ReadFileTool()
        self._cmd_tool = RestrictedCommandTool()

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="system",
            version="1.0.0",
            description="Provides local system diagnostics, datetime, safe file operations, and math evaluation.",
            author="JARVIS Core Team",
            capabilities=[
                "get_current_datetime",
                "calculator",
                "get_system_status",
                "list_files",
                "read_file",
                "restricted_command",
            ],
            permissions=[
                PluginPermission.READ_ONLY,
                PluginPermission.FILESYSTEM,
                PluginPermission.SYSTEM,
            ],
        )

    def get_tools(self) -> List[BaseTool]:
        """
        Returns concrete tools provided by SystemPlugin.

        Returns:
            List[BaseTool]: Native tool implementations.
        """
        return [
            self._dt_tool,
            self._calc_tool,
            self._status_tool,
            self._list_tool,
            self._read_tool,
            self._cmd_tool,
        ]

    async def execute(self, capability: str, **kwargs: Any) -> Any:
        """
        Executes a requested system capability by delegating to concrete tools.
        """
        cap = capability.lower().strip()
        if cap in ("get_current_datetime", "datetime", "time"):
            return await self._dt_tool.execute(**kwargs)
        elif cap in ("calculator", "math", "calc"):
            return await self._calc_tool.execute(**kwargs)
        elif cap in ("get_system_status", "status", "diagnostics"):
            return await self._status_tool.execute(**kwargs)
        elif cap in ("list_files", "ls"):
            return await self._list_tool.execute(**kwargs)
        elif cap in ("read_file", "cat"):
            return await self._read_tool.execute(**kwargs)
        elif cap in ("restricted_command", "cmd"):
            return await self._cmd_tool.execute(**kwargs)
        else:
            raise ValueError(f"SystemPlugin capability '{capability}' is unknown.")
