"""
JARVIS RAG Pipeline Module.

Coordinates query execution:
Query -> Embedding -> Retrieval -> Context Construction -> Ollama Generation -> Citations formatting.
"""

import logging
import time
from typing import Any, Dict, List, Optional

from llm.base import BaseLLMClient
from rag.citations import CitationFormatter
from rag.retriever import SemanticRetriever
from rag.schemas import RAGAnswerResponse

logger = logging.getLogger(__name__)


class RAGPipeline:
    """
    RAG execution pipeline using local vector search and local Ollama LLM client.
    """

    def __init__(
        self,
        retriever: SemanticRetriever,
        llm_client: BaseLLMClient,
    ) -> None:
        """
        Initializes RAGPipeline.

        Args:
            retriever: SemanticRetriever instance.
            llm_client: Local BaseLLMClient instance (e.g. OllamaClient).
        """
        self.retriever = retriever
        self.llm_client = llm_client

    async def answer_question(
        self,
        query: str,
        top_k: int = 5,
        system_prompt: Optional[str] = None,
    ) -> RAGAnswerResponse:
        """
        Retrieves context and executes LLM generation for a user query.

        Args:
            query: User prompt question.
            top_k: Max chunks to retrieve.
            system_prompt: Optional custom system prompt.

        Returns:
            RAGAnswerResponse: Answer text, sources, and execution latency.
        """
        start_time = time.time()

        # 1. Retrieve relevant chunks
        results = self.retriever.retrieve(query=query, top_k=top_k)
        citations = CitationFormatter.format_citations(results)

        if not results:
            logger.info("No matching document chunks found for query '%s'", query)
            elapsed = time.time() - start_time
            return RAGAnswerResponse(
                query=query,
                answer="I searched your documents but found no relevant information to answer your question.",
                sources=[],
                latency_seconds=round(elapsed, 3),
            )

        # 2. Build augmented prompt
        context_blocks = []
        for idx, res in enumerate(results, 1):
            context_blocks.append(
                f"--- [Document Source {idx}: {res.filename}] ---\n{res.text}"
            )
        context_text = "\n\n".join(context_blocks)

        prompt = (
            f"Context Information from local documents:\n"
            f"{context_text}\n\n"
            f"User Question: {query}\n\n"
            f"Answer the user's question concisely using the provided document context. "
            f"If the information is not present in the documents, state that clearly."
        )

        eff_system_prompt = system_prompt or (
            "You are JARVIS, an AI assistant answering questions based on local documents. "
            "Be direct, polite, and accurate."
        )

        # 3. Generate response using local LLM
        try:
            answer_text = await self.llm_client.generate(
                prompt=prompt, system_prompt=eff_system_prompt
            )
            elapsed = time.time() - start_time

            clean_answer = (
                answer_text.strip()
                if answer_text
                else "I could not generate an answer from the retrieved document chunks."
            )

            return RAGAnswerResponse(
                query=query,
                answer=clean_answer,
                sources=citations,
                latency_seconds=round(elapsed, 3),
            )
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error("RAG LLM generation failed for '%s': %s", query, e)
            return RAGAnswerResponse(
                query=query,
                answer=f"An error occurred while querying local documents: {e}",
                sources=citations,
                latency_seconds=round(elapsed, 3),
            )
