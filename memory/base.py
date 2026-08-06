"""
JARVIS Memory Base Interface Module.

Defines the abstract base classes for managing episodic, semantic,
and relational memory stores in JARVIS.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseMemory(ABC):
    """
    Abstract Base Class for managing conversational and semantic memory.
    Subclasses can implement in-memory stores, file/JSON-based caches,
    or sophisticated local vector databases (like Chroma, Qdrant).
    """

    @abstractmethod
    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Stores an item or context into the memory database.

        Args:
            content: The text content to store.
            metadata: Optional dictionary of key-value properties.
        """
        pass

    @abstractmethod
    async def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves relevant items from the memory database using semantic search.

        Args:
            query: The search term or context description.
            limit: The maximum number of results to retrieve.

        Returns:
            List[Dict[str, Any]]: A list of matching items with content and metadata.
        """
        pass

    @abstractmethod
    async def clear(self) -> None:
        """
        Clears or resets all memory contents from the store.
        """
        pass
