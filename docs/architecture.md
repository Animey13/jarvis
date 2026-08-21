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
│       SpeechManager       │ │ JarvisCore │ │   PluginManager   │
│   (Formal State Machine:  │ │ (app/core) │ │  (plugins/)       │
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

### Interface Segregation & Dependency Inversion
All external system integrations (Language Models, Custom Plugins, Speech Synthesis, Memory Stores, UI displays) are defined as strict abstract interfaces (`ABC` / Protocols):
- `plugins/base.py` -> `BasePlugin`, `PluginToolBridge`
- `llm/base.py` -> `BaseLLMClient`
- `speech/interfaces.py` -> `AudioInput`, `SpeechRecognizer`, `SpeechSynthesizer`
- `tools/base.py` -> `BaseTool`
- `memory/base.py` -> `BaseMemory`
- `ui/base.py` -> `BaseUserInterface`

---

## 2. Custom Plugin Architecture (Phase 9)

The Custom Plugin Architecture (`plugins/`) provides a secure, modular capability expansion framework that isolates failures and bridges capabilities into `ToolRegistry`.

### Submodule Organization
- `plugins/base.py`: Defines `BasePlugin` abstract class and `PluginToolBridge` adapter.
- `plugins/permissions.py`: Defines `PluginPermission` enum (`READ_ONLY`, `NETWORK`, `FILESYSTEM`, `SYSTEM`, `EXECUTION`).
- `plugins/schemas.py`: Pydantic V2 models for `PluginMetadata` and `PluginStatus`.
- `plugins/registry.py`: Thread-safe `PluginRegistry` for plugin lookup, listing, status discovery, enable/disable toggles.
- `plugins/manager.py`: `PluginManager` handling plugin loading, lifecycle, permission checks, failure isolation, and automatic tool synchronization.
- `plugins/builtins/`: Native built-in plugins:
  - `system.py`: `SystemPlugin` bridging datetime, calculator, system diagnostics, list files, read file, and restricted commands.
  - `weather.py`: `WeatherPlugin` with `WeatherProviderInterface` (Open-Meteo REST API with offline fallback).
  - `web_search.py`: `WebSearchPlugin` with `SearchProviderInterface` (DuckDuckGo search with offline fallback).

---

## 3. Web Dashboard Architecture (Phase 8 & Phase 9)

The Web Dashboard subpackage (`web/`) provides a local, offline-first graphical user interface powered by **FastAPI**, **Pydantic**, and **WebSockets**.

### Submodule Organization
- `web/app.py`: FastAPI server setup, static file mounting, lifespan event management.
- `web/routes.py`: REST API endpoints for `/api/status`, `/api/config`, `/api/plugins`, `/api/tools`, `/api/memory`, `/api/chat`, `/api/system`, `/api/control`, `/api/events`.
- `web/websocket.py`: Thread-safe `WebSocketManager` managing connected clients and non-blocking JSON event broadcasts.
- `web/state.py`: `EventBus` publishing structured system events (`state_change`, `transcription`, `user_message`, `assistant_message`, `tool_start`, `tool_complete`, `plugin_enabled`, `plugin_disabled`, `memory_update`, `error`).
- `web/static/`: Pure HTML5, CSS3, and Vanilla JavaScript dashboard UI featuring Plugins management cards.

---

## 4. Concurrency & Failure Isolation Model

JARVIS employs **asyncio** as its core runtime.
- Plugin executions are isolated inside try/except wrappers in `BasePlugin.execute_tool`, capturing errors in `plugin.last_error` while keeping `JarvisCore` and `SpeechManager` operational.
- External API calls (Weather and Web Search) implement timeouts and graceful degradation to offline fallback responses when network access is unavailable or interrupted.
