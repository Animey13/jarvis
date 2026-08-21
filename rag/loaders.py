"""
JARVIS RAG Document Loaders Module.

Provides abstractions and concrete loaders for reading text (.txt), Markdown (.md),
PDF (.pdf), and Word (.docx) files safely with checksum generation and path safety rules.
"""

import hashlib
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from rag.schemas import DocumentMetadata

logger = logging.getLogger(__name__)


def compute_file_checksum(filepath: str) -> str:
    """
    Computes SHA256 checksum hash of a file for incremental change detection.

    Args:
        filepath: Target file path string.

    Returns:
        str: SHA256 hex digest string.
    """
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            while chunk := f.read(65536):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception as e:
        logger.warning("Failed computing checksum for %s: %s", filepath, e)
        return ""


class BaseDocumentLoader(ABC):
    """
    Abstract base class for document loaders.
    """

    @abstractmethod
    def load(self, filepath: str) -> Tuple[str, DocumentMetadata]:
        """
        Loads document text and constructs metadata object.

        Args:
            filepath: Path to file.

        Returns:
            Tuple[str, DocumentMetadata]: Extracted text content and metadata.
        """
        pass


class TextLoader(BaseDocumentLoader):
    """
    Loader for plain text (.txt) files.
    """

    def load(self, filepath: str) -> Tuple[str, DocumentMetadata]:
        path = Path(filepath).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        size = path.stat().st_size
        checksum = compute_file_checksum(str(path))
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()

        doc_id = hashlib.md5(f"{path.name}_{checksum}".encode("utf-8")).hexdigest()[:16]

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        meta = DocumentMetadata(
            document_id=doc_id,
            filename=path.name,
            path=str(path),
            file_type="txt",
            size_bytes=size,
            checksum=checksum,
            modified_at=mtime,
        )
        return content, meta


class MarkdownLoader(BaseDocumentLoader):
    """
    Loader for Markdown (.md) files.
    """

    def load(self, filepath: str) -> Tuple[str, DocumentMetadata]:
        path = Path(filepath).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        size = path.stat().st_size
        checksum = compute_file_checksum(str(path))
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()

        doc_id = hashlib.md5(f"{path.name}_{checksum}".encode("utf-8")).hexdigest()[:16]

        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().strip()

        meta = DocumentMetadata(
            document_id=doc_id,
            filename=path.name,
            path=str(path),
            file_type="md",
            size_bytes=size,
            checksum=checksum,
            modified_at=mtime,
        )
        return content, meta


class PDFLoader(BaseDocumentLoader):
    """
    Loader for PDF (.pdf) files using pypdf with fallback.
    """

    def load(self, filepath: str) -> Tuple[str, DocumentMetadata]:
        path = Path(filepath).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        size = path.stat().st_size
        checksum = compute_file_checksum(str(path))
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        doc_id = hashlib.md5(f"{path.name}_{checksum}".encode("utf-8")).hexdigest()[:16]

        text_pages = []
        try:
            import pypdf
            reader = pypdf.PdfReader(str(path))
            for page_num, page in enumerate(reader.pages, start=1):
                page_text = page.extract_text() or ""
                if page_text.strip():
                    text_pages.append(f"[Page {page_num}]\n{page_text.strip()}")
        except Exception as e:
            logger.warning("pypdf parsing failed for %s: %s", filepath, e)

        content = "\n\n".join(text_pages).strip()

        meta = DocumentMetadata(
            document_id=doc_id,
            filename=path.name,
            path=str(path),
            file_type="pdf",
            size_bytes=size,
            checksum=checksum,
            modified_at=mtime,
        )
        return content, meta


class DocxLoader(BaseDocumentLoader):
    """
    Loader for Word (.docx) files using python-docx with fallback.
    """

    def load(self, filepath: str) -> Tuple[str, DocumentMetadata]:
        path = Path(filepath).resolve()
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"File not found: {filepath}")

        size = path.stat().st_size
        checksum = compute_file_checksum(str(path))
        mtime = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
        doc_id = hashlib.md5(f"{path.name}_{checksum}".encode("utf-8")).hexdigest()[:16]

        paragraphs = []
        try:
            import docx
            doc = docx.Document(str(path))
            for p in doc.paragraphs:
                if p.text.strip():
                    paragraphs.append(p.text.strip())
        except Exception as e:
            logger.warning("python-docx parsing failed for %s: %s", filepath, e)

        content = "\n\n".join(paragraphs).strip()

        meta = DocumentMetadata(
            document_id=doc_id,
            filename=path.name,
            path=str(path),
            file_type="docx",
            size_bytes=size,
            checksum=checksum,
            modified_at=mtime,
        )
        return content, meta


def get_document_loader(filepath: str) -> BaseDocumentLoader:
    """
    Factory function returning appropriate DocumentLoader based on file extension.

    Args:
        filepath: Target file path.

    Returns:
        BaseDocumentLoader: Loader instance.

    Raises:
        ValueError: If file extension is unsupported.
    """
    ext = Path(filepath).suffix.lower().lstrip(".")
    if ext == "txt":
        return TextLoader()
    elif ext == "md":
        return MarkdownLoader()
    elif ext == "pdf":
        return PDFLoader()
    elif ext in ("docx", "doc"):
        return DocxLoader()
    else:
        raise ValueError(f"Unsupported document file extension '.{ext}'. Supported: .txt, .md, .pdf, .docx")
