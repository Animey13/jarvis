"""
JARVIS LLM Base Interface Module.

Defines the abstract base client for interacting with Language Models.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Any, Optional


class BaseLLMClient(ABC):
    """
    Abstract Base Class representing a client for Language Model inference.
    All LLM adapters (e.g., Ollama, OpenAI, Llama.cpp) must inherit from this class.
    """

    def __init__(self, model_name: str, api_base: str, timeout: float = 30.0) -> None:
        """
        Initializes the LLM Client.

        Args:
            model_name: Name of the language model to target.
            api_base: Base URL for the LLM API service.
            timeout: Maximum timeout in seconds for API calls.
        """
        self.model_name: str = model_name
        self.api_base: str = api_base
        self.timeout: float = timeout

    @abstractmethod
    async def generate(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> str:
        """
        Generates a text completion for a given prompt.

        Args:
            prompt: User prompt to complete.
            system_prompt: Optional instructions to guide model persona/rules.
            **kwargs: Extra arguments for generation parameters (e.g., temperature).

        Returns:
            str: The generated response text.
        """
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, system_prompt: Optional[str] = None, **kwargs: Any) -> AsyncIterator[str]:
        """
        Generates a streaming text completion for a given prompt, yielding words/tokens.

        Args:
            prompt: User prompt to complete.
            system_prompt: Optional instructions to guide model persona/rules.
            **kwargs: Extra arguments for generation parameters (e.g., temperature).

        Returns:
            AsyncIterator[str]: An async generator yielding parts of the generated response.
        """
        pass
