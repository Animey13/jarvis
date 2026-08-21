"""
JARVIS RAG Base Component Interface.
"""

from abc import ABC, abstractmethod


class BaseRAGComponent(ABC):
    """
    Abstract base interface for RAG components.
    """

    @property
    @abstractmethod
    def component_name(self) -> str:
        pass
