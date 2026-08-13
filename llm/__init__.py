"""
JARVIS LLM Subpackage.

This package manages interface adapters for Language Models (LLMs),
allowing offline-first local inference (e.g. Ollama, Llama.cpp) and APIs.
"""

from llm.base import BaseLLMClient
from llm.ollama import OllamaClient

__all__ = [
    "BaseLLMClient",
    "OllamaClient",
]
