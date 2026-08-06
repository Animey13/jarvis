"""
JARVIS User Interface Base Module.

Defines the abstract base classes for rendering user interface outputs and
capturing inputs.
"""

from abc import ABC, abstractmethod


class BaseUserInterface(ABC):
    """
    Abstract Base Class for managing JARVIS user interactions.
    Enables console interfaces, web overlays, or native desktop displays.
    """

    @abstractmethod
    async def display_message(self, message: str, sender: str = "JARVIS") -> None:
        """
        Displays a message on the user interface.

        Args:
            message: The string text message to display.
            sender: The entity sending the message (e.g., JARVIS, USER).
        """
        pass

    @abstractmethod
    async def prompt_user(self, prompt_text: str = "> ") -> str:
        """
        Prompts the user for text-based input.

        Args:
            prompt_text: Prefix string displayed next to input indicator.

        Returns:
            str: User response.
        """
        pass
