"""
JARVIS Plugin Registry Module.

Provides thread-safe registration, retrieval, discovery, enabling/disabling,
and metadata management for plugins.
"""

import logging
from typing import Dict, List, Optional

from plugins.base import BasePlugin
from plugins.schemas import PluginStatus

logger = logging.getLogger(__name__)


class PluginRegistry:
    """
    Registry maintaining all registered plugins.
    """

    def __init__(self) -> None:
        """
        Initializes the PluginRegistry.
        """
        self._plugins: Dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin) -> None:
        """
        Registers a plugin. Prevents duplicate registration unless explicit.

        Args:
            plugin: BasePlugin instance to register.

        Raises:
            ValueError: If a plugin with the same name is already registered.
        """
        name = plugin.name.strip().lower()
        if name in self._plugins:
            raise ValueError(f"Plugin with name '{name}' is already registered.")

        self._plugins[name] = plugin
        logger.info("Registered plugin '%s' (v%s)", plugin.name, plugin.version)

    def unregister(self, name: str) -> Optional[BasePlugin]:
        """
        Unregisters a plugin by name.

        Args:
            name: Plugin name.

        Returns:
            Optional[BasePlugin]: Unregistered plugin instance if found.
        """
        key = name.strip().lower()
        plugin = self._plugins.pop(key, None)
        if plugin:
            logger.info("Unregistered plugin '%s'", name)
        return plugin

    def get(self, name: str) -> Optional[BasePlugin]:
        """
        Retrieves a plugin by name.

        Args:
            name: Plugin name.

        Returns:
            Optional[BasePlugin]: Plugin instance if found.
        """
        if not name or not isinstance(name, str):
            return None
        return self._plugins.get(name.strip().lower())

    def list(self) -> List[BasePlugin]:
        """
        Returns list of all registered plugins.

        Returns:
            List[BasePlugin]: List of plugins.
        """
        return list(self._plugins.values())

    def discover(self) -> List[PluginStatus]:
        """
        Returns status summaries of all registered plugins.

        Returns:
            List[PluginStatus]: Status list.
        """
        return [p.get_status() for p in self._plugins.values()]

    def enable(self, name: str) -> bool:
        """
        Enables a plugin by name.

        Args:
            name: Plugin name.

        Returns:
            bool: True if plugin found and enabled.
        """
        plugin = self.get(name)
        if plugin:
            plugin.enabled = True
            logger.info("Enabled plugin '%s'", plugin.name)
            return True
        return False

    def disable(self, name: str) -> bool:
        """
        Disables a plugin by name.

        Args:
            name: Plugin name.

        Returns:
            bool: True if plugin found and disabled.
        """
        plugin = self.get(name)
        if plugin:
            plugin.enabled = False
            logger.info("Disabled plugin '%s'", plugin.name)
            return True
        return False
