"""
JARVIS RAG Text Chunker Module.

Splits document text into overlapping, bounded chunks while preserving document
metadata and character offset positions.
"""

import logging
from typing import Any, Dict, List

from rag.schemas import DocumentChunk, DocumentMetadata

logger = logging.getLogger(__name__)


class TextChunker:
    """
    Configurable document chunker providing sliding window chunk generation.
    """

    def __init__(
        self,
        chunk_size: int = 800,
        chunk_overlap: int = 120,
        min_chunk_size: int = 50,
    ) -> None:
        """
        Initializes chunker options.

        Args:
            chunk_size: Target maximum characters per chunk.
            chunk_overlap: Overlapping character count between consecutive chunks.
            min_chunk_size: Minimum character length required to keep a chunk.
        """
        self.chunk_size = max(chunk_size, 100)
        self.chunk_overlap = max(min(chunk_overlap, self.chunk_size // 2), 0)
        self.min_chunk_size = max(min_chunk_size, 10)

    def chunk_document(self, text: str, metadata: DocumentMetadata) -> List[DocumentChunk]:
        """
        Splits raw document text into chunks preserving metadata.

        Args:
            text: Full text content of document.
            metadata: DocumentMetadata instance.

        Returns:
            List[DocumentChunk]: List of generated document chunk objects.
        """
        if not text or not text.strip():
            logger.warning("Empty text passed to chunker for document '%s'", metadata.filename)
            return []

        clean_text = text.strip()
        chunks: List[DocumentChunk] = []

        start = 0
        text_length = len(clean_text)
        chunk_idx = 0

        while start < text_length:
            end = start + self.chunk_size

            # If not at text end, break chunk at clean paragraph/sentence/word boundary
            if end < text_length:
                # Look for paragraph break
                para_break = clean_text.rfind("\n\n", start + self.min_chunk_size, end)
                if para_break != -1:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    sent_break = clean_text.rfind(". ", start + self.min_chunk_size, end)
                    if sent_break != -1:
                        end = sent_break + 2
                    else:
                        # Look for space boundary
                        space_break = clean_text.rfind(" ", start + self.min_chunk_size, end)
                        if space_break != -1:
                            end = space_break + 1

            chunk_text = clean_text[start:end].strip()

            if len(chunk_text) >= self.min_chunk_size or not chunks:
                chunk_id = f"{metadata.document_id}_chk_{chunk_idx}"
                chunks.append(
                    DocumentChunk(
                        chunk_id=chunk_id,
                        document_id=metadata.document_id,
                        text=chunk_text,
                        chunk_index=chunk_idx,
                        start_char=start,
                        end_char=end,
                        metadata={
                            "filename": metadata.filename,
                            "file_type": metadata.file_type,
                            "document_id": metadata.document_id,
                        },
                    )
                )
                chunk_idx += 1

            step = end - start - self.chunk_overlap
            if step <= 0:
                step = self.chunk_size - self.chunk_overlap
            start += step

        metadata.chunk_count = len(chunks)
        return chunks
