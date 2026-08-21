"""
JARVIS RAG Citations Module.

Provides citation extraction and formatting helpers for RAG search results.
"""

from typing import Any, Dict, List
from rag.schemas import CitationSource, RAGSearchResult


class CitationFormatter:
    """
    Helper utility to format search results into structured citations.
    """

    @staticmethod
    def format_citations(results: List[RAGSearchResult]) -> List[CitationSource]:
        """
        Converts search results into structured CitationSource models.

        Args:
            results: List of RAGSearchResult items.

        Returns:
            List[CitationSource]: List of formatted citation source objects.
        """
        citations: List[CitationSource] = []
        for res in results:
            excerpt = res.text[:150].replace("\n", " ").strip() + "..."
            citations.append(
                CitationSource(
                    filename=res.filename,
                    document_id=res.document_id,
                    chunk_id=res.chunk_id,
                    score=round(res.similarity_score, 4),
                    excerpt=excerpt,
                    page=res.metadata.get("page"),
                )
            )
        return citations

    @staticmethod
    def format_citations_prompt(citations: List[CitationSource]) -> str:
        """
        Formats citations into a human-readable text footer for LLM prompts.

        Args:
            citations: List of CitationSource objects.

        Returns:
            str: Formatted citations prompt string.
        """
        if not citations:
            return ""

        lines = ["\nSources & References:"]
        for idx, src in enumerate(citations, 1):
            page_info = f", Page {src.page}" if src.page else ""
            lines.append(
                f"[{idx}] {src.filename}{page_info} (Relevance Score: {src.score:.2f})"
            )
        return "\n".join(lines)
