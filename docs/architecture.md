# JARVIS: Architectural Design & Patterns

This document details the architectural decisions and patterns selected for **JARVIS** (Local AI Assistant).

---

## 1. High-Level Architectural Patterns

JARVIS adopts **Clean Architecture** combined with **Domain-Driven Design (DDD)** concepts. This isolates the core orchestration layer from volatile infrastructure details (like specific LLM models, TTS voice libraries, or UI frontends).

```
                  ┌──────────────────────────────────────────┐
                  │              main.py (CLI)               │
                  └────────────────────┬─────────────────────┘
                                       │
                                       ▼
                  ┌──────────────────────────────────────────┐
                  │       JarvisAssistant (Orchestrator)     │
                  └──────┬──────────────┬──────────────┬─────┘
                         │              │              │
                         ▼              ▼              ▼
┌───────────────────────────┐ ┌────────────┐ ┌───────────────────┐
│       SpeechManager       │ │ JarvisCore │ │    RAGManager     │
│   (Formal State Machine:  │ │ (app/core) │ │    (rag/)         │
│  WAKING, LISTENING, etc.) │ └─────┬──────┘ └─────────┬─────────┘
└─────────────┬─────────────┘       │                  │
              │                     ▼                  ▼
              │              ┌──────────────────────────┐
              │              │       ToolRegistry       │
              │              │        (tools/)          │
              │              └────────────┬─────────────┘
              │                           │
              ▼                           ▼
┌───────────────────────────┐      ┌──────────────┐
│   Web Dashboard (FastAPI) │      │ OllamaClient │
│   REST API & WebSockets   │      └──────────────┘
└───────────────────────────┘
```

---

## 2. RAG Architecture (Phase 10)

The RAG subsystem (`rag/`) provides offline document indexing and semantic retrieval without external vector DB clouds or API keys.

### Submodule Organization
- `rag/schemas.py`: `DocumentMetadata`, `DocumentChunk`, `CitationSource`, `RAGSearchResult`, `RAGAnswerResponse`.
- `rag/loaders.py`: Document loaders (`TextLoader`, `MarkdownLoader`, `PDFLoader`, `DocxLoader`) with checksum computation (`compute_file_checksum`).
- `rag/chunker.py`: `TextChunker` sliding window splitter with configurable size, overlap, and boundary rules.
- `rag/embeddings.py`: `LocalTFIDFEmbeddingProvider` generating normalized vector representations locally on CPU.
- `rag/vector_store.py`: `LocalVectorStore` persisting document and chunk vectors to `data/rag/vector_store.json`.
- `rag/retriever.py`: `SemanticRetriever` providing cosine similarity vector search and token context bounding (`max_context_tokens`).
- `rag/pipeline.py`: `RAGPipeline` connecting search results to `OllamaClient` and formatting citations (`CitationFormatter`).
- `rag/manager.py`: `RAGManager` coordinating ingestion, incremental checksum indexing, directory scanning, deletion, and index rebuilding.
- `tools/rag_tool.py`: `SearchDocumentsTool` exposing semantic document search to `ToolRegistry` and `JarvisCore`.

---

## 3. Web Dashboard Architecture (Phases 8, 9 & 10)

The Web Dashboard subpackage (`web/`) provides a local, offline-first graphical user interface powered by **FastAPI**, **Pydantic**, and **WebSockets**.

### Submodule Organization
- `web/app.py`: FastAPI server setup, static file mounting, lifespan event management.
- `web/routes.py`: REST API endpoints for `/api/status`, `/api/config`, `/api/plugins`, `/api/rag/documents`, `/api/rag/index`, `/api/rag/rebuild`, `/api/rag/search`, `/api/tools`, `/api/memory`, `/api/chat`, `/api/system`, `/api/control`, `/api/events`.
- `web/websocket.py`: Thread-safe `WebSocketManager` broadcasting events (`rag_ingestion_started`, `rag_ingestion_completed`, `rag_index_updated`, `rag_search`).
- `web/static/`: HTML5/CSS3/Vanilla JS UI featuring Local Documents management panel.
