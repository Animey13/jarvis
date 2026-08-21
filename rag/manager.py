"""
JARVIS RAG Manager Module.

High-level manager coordinating document ingestion, directory scanning,
incremental checksum-based updates, document removal, semantic search, and index rebuilding.
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from rag.chunker import TextChunker
from rag.embeddings import LocalTFIDFEmbeddingProvider
from rag.loaders import compute_file_checksum, get_document_loader
from rag.retriever import SemanticRetriever
from rag.schemas import DocumentMetadata, RAGSearchResult
from rag.vector_store import LocalVectorStore

logger = logging.getLogger(__name__)


class RAGManager:
    """
    Manager governing document ingestion, storage, retrieval, and indexing.
    """

    def __init__(
        self,
        data_dir: str = "data/rag",
        documents_dir: str = "data/documents",
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
    ) -> None:
        """
        Initializes RAGManager.

        Args:
            data_dir: Directory for storing vector index.
            documents_dir: Approved directory for local user documents.
            chunk_size: Target characters per chunk.
            chunk_overlap: Overlap characters between chunks.
            top_k: Max chunks to retrieve per search.
            similarity_threshold: Cutoff similarity score.
        """
        self.data_dir = Path(data_dir).resolve()
        self.documents_dir = Path(documents_dir).resolve()

        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.documents_dir.mkdir(parents=True, exist_ok=True)

        self.embedding_provider = LocalTFIDFEmbeddingProvider()
        self.vector_store = LocalVectorStore(
            storage_dir=str(self.data_dir),
            embedding_provider=self.embedding_provider,
        )
        self.chunker = TextChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self.retriever = SemanticRetriever(
            vector_store=self.vector_store,
            top_k=top_k,
            similarity_threshold=similarity_threshold,
        )

    def ingest_document(self, filepath: str, force_reindex: bool = False) -> Optional[DocumentMetadata]:
        """
        Ingests a document file into the vector store, using file checksums to skip unchanged files.

        Args:
            filepath: Path to file.
            force_reindex: If True, reindexes even if checksum matches.

        Returns:
            Optional[DocumentMetadata]: Document metadata if ingested, None if unchanged or failed.
        """
        path = Path(filepath).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Document file not found: {filepath}")

        # Strict path traversal guard: ensure file resides inside approved documents_dir or data_dir
        in_docs_dir = False
        in_data_dir = False
        try:
            path.relative_to(self.documents_dir)
            in_docs_dir = True
        except ValueError:
            pass

        try:
            path.relative_to(self.data_dir)
            in_data_dir = True
        except ValueError:
            pass

        if not (in_docs_dir or in_data_dir):
            raise PermissionError(
                f"Access denied: Path '{path}' is outside approved document directories "
                f"('{self.documents_dir}' and '{self.data_dir}')."
            )

        checksum = compute_file_checksum(str(path))
        existing_doc = self.vector_store.get_document_by_filename(path.name)

        if existing_doc and not force_reindex:
            if existing_doc.get("checksum") == checksum:
                logger.info("Document '%s' unchanged. Skipping re-indexing.", path.name)
                return DocumentMetadata(**existing_doc)

        try:
            loader = get_document_loader(str(path))
            content, meta = loader.load(str(path))

            if not content:
                logger.warning("Document '%s' yielded empty content.", path.name)

            chunks = self.chunker.chunk_document(content, meta)

            if existing_doc:
                self.vector_store.delete_document(existing_doc.get("document_id"))

            self.vector_store.add_document_chunks(meta, chunks)

            try:
                from web.state import event_bus
                event_bus.publish("rag_index_updated", data={"document": meta.filename})
            except Exception:
                pass

            return meta
        except Exception as e:
            logger.error("Failed to ingest document '%s': %s", path.name, e)
            raise

    def ingest_directory(self, dir_path: Optional[str] = None) -> List[DocumentMetadata]:
        """
        Scans and ingests all supported document files in a directory.

        Args:
            dir_path: Target directory path string (defaults to self.documents_dir).

        Returns:
            List[DocumentMetadata]: List of metadata for ingested documents.
        """
        target_dir = Path(dir_path).resolve() if dir_path else self.documents_dir
        if not target_dir.exists() or not target_dir.is_dir():
            logger.warning("Directory does not exist: %s", target_dir)
            return []

        supported_exts = {".txt", ".md", ".pdf", ".docx", ".doc"}
        ingested: List[DocumentMetadata] = []

        for root, _, files in os.walk(target_dir):
            for file in files:
                ext = Path(file).suffix.lower()
                if ext in supported_exts:
                    fpath = os.path.join(root, file)
                    try:
                        meta = self.ingest_document(fpath)
                        if meta:
                            ingested.append(meta)
                    except Exception as e:
                        logger.error("Error scanning document %s: %s", fpath, e)

        return ingested

    def remove_document(self, document_id: str) -> bool:
        """Deletes a document by ID."""
        return self.vector_store.delete_document(document_id)

    def list_documents(self) -> List[Dict[str, Any]]:
        """Returns list of indexed document metadata dicts."""
        return self.vector_store.list_documents()

    def search(
        self, query: str, top_k: Optional[int] = None, similarity_threshold: Optional[float] = None
    ) -> List[RAGSearchResult]:
        """Performs semantic vector search."""
        return self.retriever.retrieve(
            query=query, top_k=top_k, similarity_threshold=similarity_threshold
        )

    def rebuild_index(self) -> int:
        """Re-scans documents directory and rebuilds entire index."""
        self.vector_store.clear()
        ingested = self.ingest_directory()
        return len(ingested)

    def clear_index(self) -> None:
        """Clears all vector store indices."""
        self.vector_store.clear()
