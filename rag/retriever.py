"""
JARVIS RAG Retriever Module.

Provides semantic retrieval, top-k filtering, relevance score thresholding,
and context token bounding.
"""

import logging
from typing import List, Optional

from rag.schemas import RAGSearchResult
from rag.vector_store import LocalVectorStore

logger = logging.getLogger(__name__)


class SemanticRetriever:
    """
    Retriever performing vector search and relevance filtering over vector store.
    """

    def __init__(
        self,
        vector_store: LocalVectorStore,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
        max_context_tokens: int = 2000,
    ) -> None:
        """
        Initializes retriever.

        Args:
            vector_store: LocalVectorStore instance.
            top_k: Default max items to return.
            similarity_threshold: Minimum similarity score cutoff.
            max_context_tokens: Maximum estimated tokens for context window.
        """
        self.vector_store = vector_store
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold
        self.max_context_tokens = max_context_tokens

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        similarity_threshold: Optional[float] = None,
    ) -> List[RAGSearchResult]:
        """
        Retrieves relevant document chunks for a query.

        Args:
            query: Search query text.
            top_k: Optional override for max results.
            similarity_threshold: Optional override for score threshold.

        Returns:
            List[RAGSearchResult]: Filtered search results.
        """
        k = top_k if top_k is not None else self.top_k
        thresh = (
            similarity_threshold
            if similarity_threshold is not None
            else self.similarity_threshold
        )

        raw_results = self.vector_store.search(
            query=query, top_k=k * 2, similarity_threshold=thresh
        )

        # Apply token context limit (estimating ~4 chars per token)
        bounded_results: List[RAGSearchResult] = []
        accumulated_chars = 0
        max_chars = self.max_context_tokens * 4

        for res in raw_results:
            chunk_len = len(res.text)
            if accumulated_chars + chunk_len > max_chars and bounded_results:
                break
            bounded_results.append(res)
            accumulated_chars += chunk_len
            if len(bounded_results) >= k:
                break

        logger.info(
            "Retrieved %d chunks for query '%s' (threshold=%.2f)",
            len(bounded_results),
            query,
            thresh,
        )
        return bounded_results
