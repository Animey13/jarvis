"""
JARVIS Plugin Permissions Module.

Defines the security permission levels for custom plugins.
"""

from enum import Enum


class PluginPermission(str, Enum):
    """
    Explicit security permission levels required by plugins.
    """

    READ_ONLY = "read_only"
    NETWORK = "network"
    FILESYSTEM = "filesystem"
    SYSTEM = "system"
    EXECUTION = "execution"

    @classmethod
    def has_value(cls, value: str) -> bool:
        """
        Checks if a string corresponds to a valid PluginPermission value.

        Args:
            value: Permission string to check.

        Returns:
            bool: True if valid enum value.
        """
        return value.lower() in [item.value for item in cls]
