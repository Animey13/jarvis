"""
JARVIS RAG Schemas Module.

Defines Pydantic data models for documents, chunks, metadata, search queries,
search results, and citations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class DocumentMetadata(BaseModel):
    """
    Metadata specification for ingested documents.
    """

    model_config = ConfigDict(extra="ignore")

    document_id: str = Field(..., description="Unique hash-based or UUID document identifier")
    filename: str = Field(..., description="Original filename")
    path: str = Field(..., description="Absolute path or relative storage path")
    file_type: str = Field(..., description="File extension / format (txt, md, pdf, docx)")
    size_bytes: int = Field(default=0, description="File size in bytes")
    checksum: str = Field(default="", description="MD5/SHA256 checksum hash for incremental indexing")
    chunk_count: int = Field(default=0, description="Total number of chunks generated")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when document was created/ingested",
    )
    modified_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when document file was last modified",
    )


class DocumentChunk(BaseModel):
    """
    Specification for a chunk extracted from a document.
    """

    model_config = ConfigDict(extra="ignore")

    chunk_id: str = Field(..., description="Unique identifier for chunk (e.g., doc_id_0)")
    document_id: str = Field(..., description="Parent document identifier")
    text: str = Field(..., description="Chunk text content")
    chunk_index: int = Field(default=0, description="Index of chunk within parent document")
    start_char: int = Field(default=0, description="Character start offset in original text")
    end_char: int = Field(default=0, description="Character end offset in original text")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata key-values")


class CitationSource(BaseModel):
    """
    Citation model linking generated answers to source document chunks.
    """

    model_config = ConfigDict(extra="ignore")

    filename: str
    document_id: str
    chunk_id: str
    score: float
    excerpt: str = Field(default="", description="Brief text excerpt from source chunk")
    page: Optional[int] = Field(default=None, description="Optional page number for PDFs")


class RAGSearchResult(BaseModel):
    """
    Result model returned by semantic retrieval search queries.
    """

    model_config = ConfigDict(extra="ignore")

    chunk_id: str
    document_id: str
    filename: str
    text: str
    similarity_score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGAnswerResponse(BaseModel):
    """
    Response model containing generated answer and structured citations.
    """

    model_config = ConfigDict(extra="ignore")

    query: str
    answer: str
    sources: List[CitationSource] = Field(default_factory=list)
    latency_seconds: float = Field(default=0.0)
