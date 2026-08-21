# JARVIS - Project Status & Architecture Documentation

This document maintains the high-level roadmap, architecture layout, and milestone completions for **JARVIS**, a production-grade, local, offline-capable AI Assistant.

---

## 🚀 Complete Integrated Architecture Blueprint

JARVIS is built using a clean, modular, and event-driven architecture that complies with **SOLID** principles, utilizing **asynchronous Python** to coordinate high-performance operations without blocking execution.

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

## 📦 Core Subsystems & Directory Tree

- **`app/`**: Core lifecycle controller, intelligence orchestrator, and console formatting (`assistant.py`, `core.py`, `logging_config.py`).
- **`config/`**: Cascading YAML and environment-overridden configuration manager (`config.py`, `settings.yaml`).
- **`rag/`**: Local vector embeddings, loaders, chunker, vector store, retriever, pipeline, citations, and manager (`schemas.py`, `loaders.py`, `chunker.py`, `embeddings.py`, `vector_store.py`, `retriever.py`, `pipeline.py`, `citations.py`, `manager.py`).
- **`plugins/`**: Custom plugin architecture, permissions, registry, manager, and built-in plugins (`base.py`, `permissions.py`, `schemas.py`, `registry.py`, `manager.py`, `builtins/system.py`, `builtins/weather.py`, `builtins/web_search.py`).
- **`speech/`**: Speech recognition, wake-word spotting, sounddevice stream captures, formal state machine orchestration, and neural speech synthesis (`interfaces.py`, `microphone.py`, `recognizer.py`, `wakeword.py`, `synthesizer.py`, `manager.py`).
- **`llm/`**: Async client wrapper for local language models (`base.py`, `ollama.py`).
- **`memory/`**: Short-term and persistent memory management layer (`base.py`, `local_json.py`, `manager.py`).
- **`tools/`**: Local extensible OS, status, memory, and RAG search tools registry (`base.py`, `registry.py`, `system_tools.py`, `rag_tool.py`).
- **`web/`**: Local web dashboard, REST API router, Pydantic schemas, EventBus, WebSocket connection manager, and HTML5/CSS3/JS dark terminal frontend (`app.py`, `routes.py`, `schemas.py`, `state.py`, `websocket.py`, `static/`).
- **`tests/`**: Full pytest coverage across 17 test modules (88 passing tests).

---

## 🏁 Completed Capabilities & Roadmap

- **Phase 1: Foundation (Completed)**: Unified CLI shell, cascading PyYAML settings, dual logging, SIGINT handling.
- **Phase 2: Core Intelligence & LLM Orchestration (Completed)**: `JarvisCore` intelligence orchestrator, bounded context memory, Ollama client integration, fail-safe spoken fallbacks.
- **Phase 3: Tool & Action Execution System (Completed)**: Modular `BaseTool` interface, `ToolRegistry`, parameter schema validation, safe system tools.
- **Phase 4: Memory System (Completed)**: `MemoryManager` short-term and persistent memory storage (`logs/persistent_memory.json`).
- **Phase 5: Natural Voice Interaction (Completed)**: Formal state machine (`SpeechState`), mid-speech interruption handling.
- **Phase 6: Complete System Integration (Completed)**: Unified end-to-end voice pipeline.
- **Phase 7: Product Polish & Documentation (Completed)**: Refined console UX, clean logging, system docs.
- **Phase 8: Web Dashboard & Modular GUI (Completed)**: FastAPI web dashboard (`web/`), WebSockets (`WS /ws`), REST API endpoints, HTML5/CSS3/JS frontend.
- **Phase 9: Custom Plugins & External Web API Integration (Completed)**: Plugin infrastructure (`BasePlugin`, `PluginRegistry`, `PluginManager`), permission levels, built-in System, Weather, and Web Search plugins.
- **Phase 10: Local Vector Embeddings & RAG (Completed - CURRENT)**:
  - Local vector embeddings & RAG subsystem (`rag/`) supporting `.txt`, `.md`, `.pdf`, `.docx` document ingestion.
  - Local `LocalTFIDFEmbeddingProvider`, sliding-window `TextChunker`, persistent `LocalVectorStore` (`data/rag/vector_store.json`), and `SemanticRetriever`.
  - Incremental checksum-based document indexing skipping unchanged files.
  - `SearchDocumentsTool` registered with `ToolRegistry` and `JarvisCore` for natural voice queries ("Jarvis, what does my resume say about machine learning?").
  - Web dashboard REST endpoints (`/api/rag/*`) and WebSocket events (`rag_ingestion_completed`, `rag_index_updated`, `rag_search`).

---

## ✅ Runtime Verification & Test Status

- 88 passing automated unit and integration tests across 17 test modules covering:
  - Document loaders (TXT, MD, PDF, DOCX), text chunking, local embeddings, vector store persistence
  - Incremental indexing, semantic retrieval, citation formatting, SearchDocumentsTool
  - Web dashboard RAG REST API endpoints and WebSocket events
  - Complete voice and intelligence pipeline integration

---

## 🧪 How to Verify & Test

Execute the full suite of automated unit and integration tests:
```bash
pytest -v
```

To run the interactive assistant console:
```bash
python3 main.py start
```

To run the Web Dashboard:
```bash
python3 main.py dashboard
```
