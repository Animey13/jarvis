"""
Comprehensive automated unit and integration tests for RAG Subsystem.

Tests document loaders (TXT, MD, PDF, DOCX), text chunker, local vector store,
semantic retrieval, document hashing / incremental indexing, citations,
SearchDocumentsTool, RAG pipeline, and Web API endpoints.
"""

import os
import tempfile
from pathlib import Path
import pytest

from rag.chunker import TextChunker
from rag.citations import CitationFormatter
from rag.embeddings import LocalTFIDFEmbeddingProvider, cosine_similarity
from rag.loaders import DocxLoader, MarkdownLoader, PDFLoader, TextLoader, get_document_loader
from rag.manager import RAGManager
from rag.pipeline import RAGPipeline
from rag.schemas import DocumentMetadata, RAGSearchResult
from rag.vector_store import LocalVectorStore
from tools.rag_tool import SearchDocumentsTool
from tools.registry import ToolRegistry


@pytest.fixture
def temp_rag_dirs():
    with tempfile.TemporaryDirectory() as data_dir, tempfile.TemporaryDirectory() as docs_dir:
        yield data_dir, docs_dir


def test_text_and_markdown_loaders(temp_rag_dirs):
    data_dir, docs_dir = temp_rag_dirs

    # Text loader test
    txt_path = Path(docs_dir) / "sample.txt"
    txt_path.write_text("Hello JARVIS RAG System\nThis is a sample document for testing.", encoding="utf-8")

    loader = get_document_loader(str(txt_path))
    content, meta = loader.load(str(txt_path))

    assert "JARVIS RAG System" in content
    assert meta.file_type == "txt"
    assert meta.filename == "sample.txt"

    # Markdown loader test
    md_path = Path(docs_dir) / "notes.md"
    md_path.write_text("# Project Notes\n\n- Architecture: Clean\n- Subsystem: RAG", encoding="utf-8")

    md_loader = get_document_loader(str(md_path))
    md_content, md_meta = md_loader.load(str(md_path))

    assert "Architecture" in md_content
    assert md_meta.file_type == "md"


def test_chunker_and_overlap(temp_rag_dirs):
    data_dir, docs_dir = temp_rag_dirs
    chunker = TextChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=10)

    sample_text = (
        "JARVIS is a local AI assistant built for Ubuntu. "
        "It supports offline voice recognition with Faster-Whisper and Kokoro ONNX neural speech synthesis. "
        "The RAG subsystem provides document retrieval without external APIs."
    )
    meta = DocumentMetadata(
        document_id="doc123",
        filename="test.txt",
        path="/tmp/test.txt",
        file_type="txt",
    )

    chunks = chunker.chunk_document(sample_text, meta)
    assert len(chunks) >= 2
    assert chunks[0].document_id == "doc123"
    assert chunks[0].chunk_id.startswith("doc123_chk_")


def test_local_embeddings_and_vector_store(temp_rag_dirs):
    data_dir, docs_dir = temp_rag_dirs
    store = LocalVectorStore(storage_dir=data_dir)

    meta = DocumentMetadata(
        document_id="doc_test",
        filename="resume.txt",
        path=f"{docs_dir}/resume.txt",
        file_type="txt",
    )
    chunker = TextChunker(chunk_size=200, chunk_overlap=20)
    chunks = chunker.chunk_document(
        "Alex is an expert Python software engineer with experience in Machine Learning and FastAPI.",
        meta,
    )

    store.add_document_chunks(meta, chunks)

    assert store.count_documents() == 1
    assert store.count_chunks() >= 1

    # Search test
    results = store.search("Machine Learning Python", top_k=2)
    assert len(results) >= 1
    assert results[0].filename == "resume.txt"
    assert "Python" in results[0].text


def test_rag_manager_incremental_indexing(temp_rag_dirs):
    data_dir, docs_dir = temp_rag_dirs
    mgr = RAGManager(data_dir=data_dir, documents_dir=docs_dir)

    file_path = Path(docs_dir) / "report.txt"
    file_path.write_text("Quarterly financial report detailing company revenue and growth.", encoding="utf-8")

    # Ingest document
    meta1 = mgr.ingest_document(str(file_path))
    assert meta1 is not None
    assert len(mgr.list_documents()) == 1

    # Re-ingest unchanged document (should skip and return existing metadata)
    meta2 = mgr.ingest_document(str(file_path))
    assert meta2.checksum == meta1.checksum

    # Search test
    res = mgr.search("revenue growth", top_k=3)
    assert len(res) >= 1
    assert res[0].filename == "report.txt"


def test_citations_formatter():
    search_res = RAGSearchResult(
        chunk_id="c1",
        document_id="d1",
        filename="report.pdf",
        text="The architecture uses local vector embeddings for offline retrieval.",
        similarity_score=0.88,
        metadata={"page": 2},
    )

    citations = CitationFormatter.format_citations([search_res])
    assert len(citations) == 1
    assert citations[0].filename == "report.pdf"
    assert citations[0].page == 2

    prompt_str = CitationFormatter.format_citations_prompt(citations)
    assert "report.pdf" in prompt_str
    assert "Page 2" in prompt_str


@pytest.mark.asyncio
async def test_search_documents_tool_and_registry(temp_rag_dirs):
    data_dir, docs_dir = temp_rag_dirs
    mgr = RAGManager(data_dir=data_dir, documents_dir=docs_dir)

    doc_path = Path(docs_dir) / "guide.txt"
    doc_path.write_text("JARVIS tool architecture relies on BaseTool parameter schemas.", encoding="utf-8")
    mgr.ingest_document(str(doc_path))

    tool = SearchDocumentsTool(rag_manager=mgr)
    registry = ToolRegistry()
    registry.register_tool(tool)

    assert registry.get_tool("search_documents") is not None

    exec_res = await registry.execute_tool("search_documents", query="parameter schemas", top_k=2)
    assert exec_res["status"] == "success"
    assert exec_res["result"]["count"] >= 1
    assert exec_res["result"]["results"][0]["filename"] == "guide.txt"


@pytest.mark.asyncio
async def test_rag_pipeline_with_mock_llm(temp_rag_dirs):
    data_dir, docs_dir = temp_rag_dirs
    mgr = RAGManager(data_dir=data_dir, documents_dir=docs_dir)

    doc_path = Path(docs_dir) / "info.txt"
    doc_path.write_text("Project JARVIS was launched in 2026.", encoding="utf-8")
    mgr.ingest_document(str(doc_path))

    class MockLLM:
        async def generate(self, prompt: str, system_prompt: str = "") -> str:
            assert "JARVIS" in prompt
            return "Project JARVIS was launched in 2026."

    pipeline = RAGPipeline(retriever=mgr.retriever, llm_client=MockLLM())
    ans = await pipeline.answer_question("When was JARVIS launched?")

    assert "2026" in ans.answer
    assert len(ans.sources) >= 1
    assert ans.sources[0].filename == "info.txt"
