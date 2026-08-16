"""
JARVIS Core Intelligence Layer Module.

Provides the primary intelligence orchestrator (`JarvisCore`) that manages
conversation context memory, system prompt rules, asynchronous LLM execution,
latency tracking, and graceful fallback handling for JARVIS.
"""

import logging
import time
from typing import List, Optional

from config.config import Settings
from llm.base import BaseLLMClient
from llm.ollama import OllamaClient

logger = logging.getLogger(__name__)

# Default explicit system prompt establishing JARVIS persona and rules
DEFAULT_SYSTEM_PROMPT: str = (
    "You are JARVIS, a local personal AI assistant. "
    "Provide short, concise, and natural spoken responses suitable for voice interaction. "
    "Do not use markdown formatting, bullet points, or verbose technical explanations unless requested. "
    "Acknowledge commands naturally and politely."
)

# Default short spoken fallback when the LLM service fails or is unreachable
DEFAULT_FALLBACK_RESPONSE: str = "I'm sorry, I am currently unable to reach my local language model."


class ConversationTurn:
    """
    Represents a single turn in conversation context memory.
    """

    def __init__(self, role: str, content: str) -> None:
        """
        Initializes a ConversationTurn.

        Args:
            role: The participant role ('user' or 'assistant').
            content: The text content of the turn.
        """
        self.role: str = role
        self.content: str = content


class JarvisCore:
    """
    Dedicated JARVIS Core Intelligence Orchestrator.
    Manages conversational context, system prompts, LLM invocations,
    latency tracking, and fail-safe fallbacks.
    """

    def __init__(
        self,
        settings: Settings,
        llm_client: Optional[BaseLLMClient] = None,
        max_context_length: int = 10,
        system_prompt: str = DEFAULT_SYSTEM_PROMPT,
        fallback_response: str = DEFAULT_FALLBACK_RESPONSE
    ) -> None:
        """
        Initializes the JARVIS Core Intelligence orchestrator.

        Args:
            settings: Loaded system configuration settings.
            llm_client: Optional custom LLM client instance; defaults to OllamaClient using settings.
            max_context_length: Maximum number of conversation turns retained in memory.
            system_prompt: System prompt defining persona and behavioral rules.
            fallback_response: Spoken fallback text returned when LLM generation fails.
        """
        self.settings: Settings = settings
        self.max_context_length: int = max_context_length
        self.system_prompt: str = system_prompt
        self.fallback_response: str = fallback_response
        self.history: List[ConversationTurn] = []

        if llm_client is not None:
            self.llm_client: BaseLLMClient = llm_client
        else:
            logger.info("Initializing default OllamaClient in JarvisCore...")
            self.llm_client = OllamaClient(
                model_name=self.settings.llm.model,
                api_base=self.settings.llm.api_base,
                timeout=self.settings.llm.timeout
            )

    def add_turn(self, role: str, content: str) -> None:
        """
        Adds a conversation turn to context memory, truncating if context limit is exceeded.

        Args:
            role: Role of the message sender ('user' or 'assistant').
            content: Message content.
        """
        self.history.append(ConversationTurn(role=role, content=content))
        if len(self.history) > self.max_context_length:
            overflow = len(self.history) - self.max_context_length
            self.history = self.history[overflow:]

    def clear_context(self) -> None:
        """
        Clears all retained conversation history.
        """
        self.history.clear()

    def build_prompt(self, user_text: str) -> str:
        """
        Formats conversation history and current user text into a structured prompt.

        Args:
            user_text: Current user input text.

        Returns:
            str: Formatted context prompt.
        """
        prompt_parts: List[str] = []
        if self.history:
            prompt_parts.append("Recent conversation history:")
            for turn in self.history:
                role_label = turn.role.upper()
                prompt_parts.append(f"{role_label}: {turn.content}")
            prompt_parts.append("")

        prompt_parts.append(f"USER: {user_text}")
        return "\n".join(prompt_parts)

    async def respond(self, user_text: str) -> str:
        """
        Main public interface method: receives user text, queries LLM asynchronously,
        updates context memory, logs metrics/latency, and returns response.

        Args:
            user_text: Transcribed input text from user.

        Returns:
            str: Generated natural language response or fallback message.
        """
        if not user_text or not user_text.strip():
            logger.warning("JarvisCore received empty user text input.")
            return "I didn't hear anything. How can I help you?"

        clean_input = user_text.strip()
        logger.info("JarvisCore received command: '%s'", clean_input)

        full_prompt = self.build_prompt(clean_input)
        start_time = time.time()

        logger.info(
            "JarvisCore starting LLM request [Provider: %s, Model: %s, API: %s, Timeout: %.1fs]...",
            self.settings.llm.provider,
            self.llm_client.model_name,
            self.llm_client.api_base,
            self.llm_client.timeout
        )

        try:
            response_text = await self.llm_client.generate(
                prompt=full_prompt,
                system_prompt=self.system_prompt
            )
            elapsed_time = time.time() - start_time

            if not response_text or not response_text.strip():
                logger.warning("LLM request completed in %.2fs but yielded empty response text.", elapsed_time)
                return self.fallback_response

            clean_response = response_text.strip()
            logger.info(
                "LLM request completed successfully in %.2fs (~%d chars). Response: '%s'",
                elapsed_time,
                len(clean_response),
                clean_response
            )

            # Store successful turn in memory
            self.add_turn("user", clean_input)
            self.add_turn("assistant", clean_response)

            return clean_response

        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error("LLM request failed after %.2fs with error: %s", elapsed_time, e, exc_info=True)
            return self.fallback_response
