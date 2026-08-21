"""
JARVIS Local Persistent Vector Store Module.

Implements a local, persistent vector database in `data/rag/vector_store.json`
supporting document and chunk indexing, persistent vector storage, cosine similarity
search, and incremental checksum updates.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from rag.embeddings import LocalTFIDFEmbeddingProvider, cosine_similarity
from rag.schemas import DocumentChunk, DocumentMetadata, RAGSearchResult

logger = logging.getLogger(__name__)


class LocalVectorStore:
    """
    Local disk-backed vector database persisting index to JSON inside data directory.
    """

    def __init__(
        self,
        storage_dir: str = "data/rag",
        embedding_provider: Optional[LocalTFIDFEmbeddingProvider] = None,
    ) -> None:
        """
        Initializes local persistent vector store.

        Args:
            storage_dir: Directory where vector index JSON file is persisted.
            embedding_provider: Optional custom EmbeddingProvider instance.
        """
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "vector_store.json"

        self.embedding_provider = embedding_provider or LocalTFIDFEmbeddingProvider()

        # In-memory index structures
        self._documents: Dict[str, Dict[str, Any]] = {}  # doc_id -> metadata dict
        self._chunks: Dict[str, Dict[str, Any]] = {}     # chunk_id -> chunk & vector dict

        self._load_index()

    def _load_index(self) -> None:
        """Loads persisted index from disk if present."""
        if not self.index_file.exists():
            return

        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._documents = data.get("documents", {})
                self._chunks = data.get("chunks", {})
            logger.info(
                "Loaded local vector store index (%d documents, %d chunks)",
                len(self._documents),
                len(self._chunks),
            )
        except Exception as e:
            logger.error("Failed loading vector store index file %s: %s", self.index_file, e)

    def _save_index(self) -> None:
        """Persists current in-memory index to disk."""
        try:
            temp_file = self.index_file.with_suffix(".tmp")
            data = {"documents": self._documents, "chunks": self._chunks}
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_file, self.index_file)
        except Exception as e:
            logger.error("Failed saving vector store index to %s: %s", self.index_file, e)

    def add_document_chunks(
        self, metadata: DocumentMetadata, chunks: List[DocumentChunk]
    ) -> None:
        """
        Indexes document metadata and generates vector embeddings for all document chunks.

        Args:
            metadata: DocumentMetadata object.
            chunks: List of DocumentChunk objects.
        """
        # Store document metadata
        self._documents[metadata.document_id] = metadata.model_dump()

        # Embed and store chunks
        for chk in chunks:
            vector = self.embedding_provider.embed_text(chk.text)
            self._chunks[chk.chunk_id] = {
                "chunk_id": chk.chunk_id,
                "document_id": chk.document_id,
                "text": chk.text,
                "chunk_index": chk.chunk_index,
                "metadata": chk.metadata,
                "vector": vector,
            }

        self._save_index()
        logger.info(
            "Indexed document '%s' (%d chunks)", metadata.filename, len(chunks)
        )

    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves document metadata dict by ID."""
        return self._documents.get(document_id)

    def get_document_by_filename(self, filename: str) -> Optional[Dict[str, Any]]:
        """Retrieves document metadata dict by filename."""
        for doc in self._documents.values():
            if doc.get("filename") == filename:
                return doc
        return None

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns list of all indexed document metadata objects."""
        return list(self._documents.values())

    def delete_document(self, document_id: str) -> bool:
        """
        Deletes a document and all its chunks from the vector store.

        Args:
            document_id: Target document ID.

        Returns:
            bool: True if document was found and removed.
        """
        if document_id not in self._documents:
            return False

        del self._documents[document_id]

        # Delete all chunks belonging to document
        chunk_ids_to_del = [
            cid for cid, chk in self._chunks.items() if chk.get("document_id") == document_id
        ]
        for cid in chunk_ids_to_del:
            del self._chunks[cid]

        self._save_index()
        logger.info("Deleted document '%s' and %d chunks", document_id, len(chunk_ids_to_del))
        return True

    def search(
        self, query: str, top_k: int = 5, similarity_threshold: float = 0.1
    ) -> List[RAGSearchResult]:
        """
        Performs semantic vector similarity search against indexed chunks.

        Args:
            query: Search query text.
            top_k: Max results count.
            similarity_threshold: Minimum cosine similarity score.

        Returns:
            List[RAGSearchResult]: Ranked search results.
        """
        if not query or not query.strip() or not self._chunks:
            return []

        query_vec = self.embedding_provider.embed_text(query)
        scored_results: List[Tuple[float, Dict[str, Any]]] = []

        for chk in self._chunks.values():
            score = cosine_similarity(query_vec, chk.get("vector", []))
            if score >= similarity_threshold:
                scored_results.append((score, chk))

        # Sort descending by similarity score
        scored_results.sort(key=lambda x: x[0], reverse=True)

        results: List[RAGSearchResult] = []
        for score, chk in scored_results[:top_k]:
            doc_meta = self._documents.get(chk.get("document_id"), {})
            filename = doc_meta.get("filename", "unknown")
            results.append(
                RAGSearchResult(
                    chunk_id=chk.get("chunk_id"),
                    document_id=chk.get("document_id"),
                    filename=filename,
                    text=chk.get("text"),
                    similarity_score=score,
                    metadata=chk.get("metadata", {}),
                )
            )

        return results

    def count_documents(self) -> int:
        return len(self._documents)

    def count_chunks(self) -> int:
        return len(self._chunks)

    def clear(self) -> None:
        """Clears all indexed documents and chunks."""
        self._documents.clear()
        self._chunks.clear()
        self._save_index()
        logger.info("Cleared vector store index.")
