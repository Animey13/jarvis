"""
JARVIS RAG Search Documents Tool Module.

Provides the `search_documents` tool conforming to BaseTool for the ToolRegistry.
"""

from typing import Any, Dict, Optional
from rag.manager import RAGManager
from tools.base import BaseTool


class SearchDocumentsTool(BaseTool):
    """
    Tool allowing JARVIS to search local user documents (resumes, reports, notes) semantically.
    """

    def __init__(self, rag_manager: Optional[RAGManager] = None) -> None:
        """
        Initializes tool.

        Args:
            rag_manager: Optional RAGManager instance.
        """
        self.rag_manager = rag_manager

    @property
    def name(self) -> str:
        return "search_documents"

    @property
    def description(self) -> str:
        return (
            "Performs a semantic vector search over ingested local documents "
            "(PDFs, Word docs, Markdown, text files). Use this when asked questions "
            "about user files, resume, project reports, or notes."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "required": True,
                "description": "Semantic query string to search across indexed documents.",
            },
            "top_k": {
                "type": "integer",
                "required": False,
                "description": "Number of document chunks to retrieve (defaults to 3).",
            },
        }

    async def execute(self, query: str = "", top_k: int = 3, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes document search and returns matching text chunks and citations.
        """
        if not query or not str(query).strip():
            return {"query": query, "error": "Search query string cannot be empty."}

        if self.rag_manager is None:
            self.rag_manager = RAGManager()

        results = self.rag_manager.search(query=query, top_k=top_k)

        if not results:
            return {
                "query": query,
                "count": 0,
                "results": [],
                "message": "No matching document content found.",
            }

        formatted_results = []
        for r in results:
            formatted_results.append(
                {
                    "filename": r.filename,
                    "chunk_id": r.chunk_id,
                    "similarity_score": round(r.similarity_score, 3),
                    "text": r.text,
                }
            )

        return {
            "query": query,
            "count": len(formatted_results),
            "results": formatted_results,
        }
