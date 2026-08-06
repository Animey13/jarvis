"""
JARVIS Tools Base Interface Module.

Defines the abstract base classes for tools and actions that can be registered
and executed dynamically by JARVIS.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """
    Abstract Base Class representing an executable system tool.
    Any custom tool (e.g., file system operation, web search, weather check)
    should inherit from this and register with the Tool Registry.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The unique identifying name of the tool.

        Returns:
            str: The tool name.
        """
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """
        A descriptive explanation of what the tool does and when to use it.
        This description will be consumed by LLM system prompts for tool calling.

        Returns:
            str: The tool description.
        """
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Any:
        """
        Executes the tool with the provided arguments.

        Args:
            **kwargs: Dynamic arguments required for tool execution.

        Returns:
            Any: The result of the execution.
        """
        pass
