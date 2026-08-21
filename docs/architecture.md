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
│       SpeechManager       │ │ JarvisCore │ │   MemoryManager   │
│   (Formal State Machine:  │ │ (app/core) │ │ (Short/Persistent)│
│  WAKING, LISTENING, etc.) │ └─────┬──────┘ └───────────────────┘
└─────────────┬─────────────┘       │
              │                     ▼
              │              ┌──────────────┐
              │              │ ToolRegistry │
              │              │  (tools/)    │
              │              └──────┬───────┘
              │                     │
              ▼                     ▼
┌───────────────────────────┐┌──────────────┐
│   Web Dashboard (FastAPI) ││ OllamaClient │
│   REST API & WebSockets   │└──────────────┘
└───────────────────────────┘
```

### Interface Segregation & Dependency Inversion
All external system integrations (Language Models, Speech Synthesis, Memory Stores, UI displays) are defined as strict abstract interfaces (`ABC` / Protocols) under their respective directories:
- `llm/base.py` -> `BaseLLMClient`
- `speech/interfaces.py` -> `AudioInput`, `SpeechRecognizer`, `SpeechSynthesizer`
- `tools/base.py` -> `BaseTool`
- `memory/base.py` -> `BaseMemory`
- `ui/base.py` -> `BaseUserInterface`

---

## 2. Web Dashboard Architecture (Phase 8)

The Web Dashboard subpackage (`web/`) provides a local, offline-first graphical user interface powered by **FastAPI**, **Pydantic**, and **WebSockets**.

### Submodule Organization
- `web/app.py`: FastAPI server setup, static file mounting, lifespan event management.
- `web/routes.py`: REST API endpoints for `/api/status`, `/api/config`, `/api/tools`, `/api/memory`, `/api/chat`, `/api/system`, `/api/control`, `/api/events`.
- `web/websocket.py`: Thread-safe `WebSocketManager` managing connected clients and non-blocking JSON event broadcasts.
- `web/state.py`: `EventBus` publishing structured system events (`state_change`, `transcription`, `user_message`, `assistant_message`, `tool_start`, `tool_complete`, `memory_update`, `error`) and `WebStateManager` aggregating application references.
- `web/schemas.py`: Typed Pydantic data models for request validation and response formatting.
- `web/static/`: Pure HTML5, CSS3, and Vanilla JavaScript dashboard UI (zero external CDN or framework dependencies).

### Local Security Boundaries
- **Local IP Binding**: Binds exclusively to `127.0.0.1` by default to prevent external network exposure.
- **Controlled System Access**: File operations, command executions, and memory operations enforce strict allowlist and file size limits defined in the tool registry.
- **Non-Blocking Execution**: Web calls route through `JarvisCore` asynchronously without blocking the voice loop or main event loop.

---

## 3. SOLID Principles Applied

### Single Responsibility Principle (SRP)
- `config/config.py` loads settings from files/environments and resolves values.
- `app/logging_config.py` configures console formatters and rotating files.
- `app/core.py` manages LLM requests, system prompts, context bounding, and tool execution decisions.
- `speech/manager.py` governs the formal voice interaction state machine.
- `web/routes.py` translates REST requests into component method calls.

### Open/Closed Principle (OCP)
The registration systems for tools (`ToolRegistry`) and memory formats are open to extension (new tools can be added without modifying orchestration logic).

---

## 4. Concurrency & Event Loop Model

JARVIS employs **asyncio** as its core runtime.
- Blocking functions (such as reading terminal inputs or executing subprocess commands) run in separate executor thread pools (`loop.run_in_executor(None, ...)`).
- WebSockets broadcast events asynchronously using non-blocking tasks (`loop.create_task(...)`), ensuring high-throughput UI updates without interrupting audio streaming or speech recognition.

---

## 5. Platform Constraints & Standards
- **Ubuntu 24.04+ & Python 3.12+ Compatibility**: Standard POSIX signal capturing (`SIGINT` and `SIGTERM`) on the event loop for graceful teardowns.
- **Offline First**: Zero cloud dependencies or external CDN requirements.
