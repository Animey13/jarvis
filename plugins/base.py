"""
JARVIS Plugins Base Module.

Defines the base structure and standard interface for developing and registering
dynamic extensions or plugins for JARVIS.
"""

from abc import ABC, abstractmethod


class BasePlugin(ABC):
    """
    Abstract Base Class for third-party or modular plugins.
    Plugins are discoverable blocks of code loaded at run-time.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The unique user-friendly name of the plugin.

        Returns:
            str: The name of the plugin.
        """
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """
        The current semantic version of the plugin.

        Returns:
            str: The version string.
        """
        pass

    @abstractmethod
    async def initialize(self) -> None:
        """
        Lifecycle hook invoked immediately after loading the plugin.
        Perform any registration, database migration, or network connection here.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Lifecycle hook invoked immediately prior to system unloading or shutdown.
        Safely release database handles, file descriptors, or processes.
        """
        pass
