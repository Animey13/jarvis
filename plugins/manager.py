"""
JARVIS Plugin Manager Module.

Manages plugin loading, initialization, lifecycle, failure isolation,
permission validation, and bridging tools to ToolRegistry.
"""

import importlib
import logging
import os
import pkgutil
from typing import Any, Dict, List, Optional

from plugins.base import BasePlugin
from plugins.permissions import PluginPermission
from plugins.registry import PluginRegistry
from plugins.schemas import PluginStatus
from tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manager responsible for loading, bridging, and executing plugins.
    """

    def __init__(
        self,
        tool_registry: Optional[ToolRegistry] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Initializes PluginManager.

        Args:
            tool_registry: Optional ToolRegistry instance to register bridged tools into.
            config: Optional plugins configuration dictionary.
        """
        self.registry = PluginRegistry()
        self.tool_registry = tool_registry
        self.config: Dict[str, Any] = config or {}

    async def initialize(self) -> None:
        """
        Loads built-in plugins and dynamically loads plugins from the plugins directory.
        Synchronizes tools with ToolRegistry if attached.
        """
        logger.info("Initializing PluginManager...")
        await self._load_builtin_plugins()
        await self._load_directory_plugins()
        self.sync_tools_with_registry()

    async def shutdown(self) -> None:
        """
        Gracefully shuts down all loaded plugins.
        """
        logger.info("Shutting down PluginManager...")
        for plugin in self.registry.list():
            try:
                await plugin.shutdown()
            except Exception as e:
                logger.error("Error shutting down plugin '%s': %s", plugin.name, e)

    def register_plugin(self, plugin: BasePlugin) -> bool:
        """
        Registers a plugin instance, validates permissions and configuration, and registers its tools.

        Args:
            plugin: BasePlugin instance.

        Returns:
            bool: True if successfully registered.
        """
        try:
            plugin_cfg = self.config.get(plugin.name, {})
            if isinstance(plugin_cfg, dict) and plugin_cfg.get("enabled") is False:
                plugin.enabled = False
            elif self.config.get(f"{plugin.name}_enabled") is False:
                plugin.enabled = False

            for perm in plugin.permissions:
                if not isinstance(perm, PluginPermission) and not PluginPermission.has_value(str(perm)):
                    logger.warning(
                        "Plugin '%s' declared unknown permission '%s'.",
                        plugin.name,
                        perm,
                    )

            self.registry.register(plugin)
            self.sync_tools_with_registry()
            return True
        except Exception as e:
            logger.error("Failed to register plugin '%s': %s", getattr(plugin, "name", "unknown"), e)
            return False

    def sync_tools_with_registry(self) -> None:
        """
        Bridges plugin tools to the attached ToolRegistry for enabled plugins.
        """
        if not self.tool_registry:
            return

        for plugin in self.registry.list():
            if not plugin.enabled:
                continue
            for tool in plugin.get_tools():
                self.tool_registry.register_tool(tool)

    async def _load_builtin_plugins(self) -> None:
        """
        Imports and instantiates built-in plugins from plugins.builtins.
        """
        builtin_specs = [
            ("plugins.builtins.system", "SystemPlugin"),
            ("plugins.builtins.weather", "WeatherPlugin"),
            ("plugins.builtins.web_search", "WebSearchPlugin"),
        ]

        for mod_path, class_name in builtin_specs:
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, class_name, None)
                if cls and issubclass(cls, BasePlugin):
                    plugin_key = class_name.lower().replace("plugin", "")
                    plugin_cfg = self.config.get(plugin_key, {})
                    plugin_instance = cls(config=plugin_cfg)
                    await plugin_instance.initialize()
                    self.register_plugin(plugin_instance)
            except ImportError:
                logger.debug("Built-in plugin module '%s' not yet available.", mod_path)
            except Exception as e:
                logger.exception("Failed to load built-in plugin '%s': %s", mod_path, e)

    async def _load_directory_plugins(self) -> None:
        """
        Scans plugins directory for external plugin modules (excluding builtins and core files).
        """
        plugins_dir = os.path.dirname(__file__)
        if not os.path.exists(plugins_dir):
            return

        ignored_files = {
            "base.py",
            "manager.py",
            "permissions.py",
            "registry.py",
            "schemas.py",
            "__init__.py",
        }

        for _, modname, ispkg in pkgutil.iter_modules([plugins_dir]):
            if ispkg or modname in ("builtins", "tests"):
                continue
            filename = f"{modname}.py"
            if filename in ignored_files:
                continue

            try:
                mod = importlib.import_module(f"plugins.{modname}")
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BasePlugin)
                        and attr is not BasePlugin
                    ):
                        plugin_key = attr_name.lower().replace("plugin", "")
                        plugin_cfg = self.config.get(plugin_key, {})
                        instance = attr(config=plugin_cfg)
                        await instance.initialize()
                        self.register_plugin(instance)
            except Exception as e:
                logger.error("Failed loading external plugin '%s': %s", modname, e)

    def get_plugin_statuses(self) -> List[PluginStatus]:
        """
        Returns status models for all managed plugins.

        Returns:
            List[PluginStatus]: Plugin status objects.
        """
        return self.registry.discover()

    def enable_plugin(self, name: str) -> bool:
        """
        Enables a plugin and synchronizes tools.

        Args:
            name: Plugin name.

        Returns:
            bool: True if enabled.
        """
        res = self.registry.enable(name)
        if res:
            self.sync_tools_with_registry()
        return res

    def disable_plugin(self, name: str) -> bool:
        """
        Disables a plugin.

        Args:
            name: Plugin name.

        Returns:
            bool: True if disabled.
        """
        return self.registry.disable(name)
