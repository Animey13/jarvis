"""
JARVIS RAG Package Initialization.
"""

from rag.base import BaseRAGComponent
from rag.chunker import TextChunker
from rag.citations import CitationFormatter
from rag.embeddings import EmbeddingProvider, LocalTFIDFEmbeddingProvider
from rag.loaders import BaseDocumentLoader, DocxLoader, MarkdownLoader, PDFLoader, TextLoader, get_document_loader
from rag.manager import RAGManager
from rag.pipeline import RAGPipeline
from rag.retriever import SemanticRetriever
from rag.schemas import CitationSource, DocumentChunk, DocumentMetadata, RAGAnswerResponse, RAGSearchResult
from rag.vector_store import LocalVectorStore

__all__ = [
    "BaseRAGComponent",
    "TextChunker",
    "CitationFormatter",
    "EmbeddingProvider",
    "LocalTFIDFEmbeddingProvider",
    "BaseDocumentLoader",
    "TextLoader",
    "MarkdownLoader",
    "PDFLoader",
    "DocxLoader",
    "get_document_loader",
    "RAGManager",
    "RAGPipeline",
    "SemanticRetriever",
    "DocumentMetadata",
    "DocumentChunk",
    "CitationSource",
    "RAGSearchResult",
    "RAGAnswerResponse",
    "LocalVectorStore",
]
