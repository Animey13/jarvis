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
│       SpeechManager       │ │ JarvisCore │ │   PluginManager   │
│   (Formal State Machine:  │ │ (app/core) │ │   (plugins/)      │
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
- **`plugins/`**: Custom plugin architecture, permission enums, registry, manager, and built-in plugins (`base.py`, `permissions.py`, `schemas.py`, `registry.py`, `manager.py`, `builtins/system.py`, `builtins/weather.py`, `builtins/web_search.py`).
- **`speech/`**: Speech recognition, wake-word spotting, sounddevice stream captures, formal state machine orchestration, and neural speech synthesis (`interfaces.py`, `microphone.py`, `recognizer.py`, `wakeword.py`, `synthesizer.py`, `manager.py`).
- **`llm/`**: Async client wrapper for local language models (`base.py`, `ollama.py`).
- **`memory/`**: Short-term and persistent memory management layer (`base.py`, `local_json.py`, `manager.py`).
- **`tools/`**: Local extensible OS, status, and memory tools registry (`base.py`, `registry.py`, `system_tools.py`).
- **`web/`**: Local web dashboard, REST API router, Pydantic schemas, EventBus, WebSocket connection manager, and HTML5/CSS3/JS dark terminal frontend (`app.py`, `routes.py`, `schemas.py`, `state.py`, `websocket.py`, `static/`).
- **`tests/`**: Full pytest coverage across 16 test modules (81 passing tests).

---

## 🏁 Completed Capabilities & Roadmap

- **Phase 1: Foundation (Completed)**: Unified CLI shell (`main.py`), cascading YAML/environment settings, dual logging, and SIGINT graceful shutdown handling.
- **Phase 2: Core Intelligence & LLM Orchestration (Completed)**: `JarvisCore` intelligence orchestrator, bounded context memory, Ollama client integration, and fail-safe spoken fallbacks.
- **Phase 3: Tool & Action Execution System (Completed)**: Modular `BaseTool` interface, thread-safe `ToolRegistry`, parameter schema validation, and safe system tools.
- **Phase 4: Memory System (Completed)**: `MemoryManager` short-term and persistent memory storage (`logs/persistent_memory.json`) with corrupted JSON recovery and memory tools.
- **Phase 5: Natural Voice Interaction (Completed)**: Formal state machine (`SpeechState`), deterministic transitions, mid-speech interruption handling (`SPEAKING -> INTERRUPTED -> LISTENING`).
- **Phase 6: Complete System Integration (Completed)**: Unified pipeline (**Microphone → Audio Capture → VAD → Wake Word → Listening → Faster-Whisper → JARVIS Core → Memory Retrieval → Tool Decision → Tool Execution → LLM Response → Kokoro TTS → Playback → Interruption Handling → Return to WAKING**).
- **Phase 7: Product Polish & Documentation (Completed)**: Refined console UX, clean logging, system docs.
- **Phase 8: Web Dashboard & Modular GUI (Completed)**: FastAPI web dashboard (`web/`), WebSocket event streaming (`WS /ws`), REST API endpoints, HTML5/CSS3/Vanilla JS frontend.
- **Phase 9: Custom Plugins & External Web API Integration (Completed - CURRENT)**:
  - Built plugin infrastructure (`BasePlugin`, `PluginRegistry`, `PluginManager`, `PluginToolBridge`).
  - Added explicit permission levels (`READ_ONLY`, `NETWORK`, `FILESYSTEM`, `SYSTEM`, `EXECUTION`).
  - Built-in plugins: `SystemPlugin`, `WeatherPlugin` (Open-Meteo REST API with offline fallbacks), `WebSearchPlugin` (DuckDuckGo search with offline fallbacks).
  - Web dashboard API integration (`GET /api/plugins`, `POST /api/plugins/{name}/enable`, `POST /api/plugins/{name}/disable`) and WebSocket plugin events.
  - Full voice pipeline plugin integration ("Jarvis, what's the weather in Jaipur?").

---

## ✅ Runtime Verification & Test Status

- 81 passing automated unit and integration tests across 16 test modules covering:
  - Plugin interface, permissions, registry, dynamic discovery, enable/disable toggles, and failure isolation
  - Built-in System, Weather, and Web Search plugins with provider abstractions and offline fallbacks
  - Web dashboard REST API endpoints and WebSocket plugin events
  - Complete system pipeline integration (`wake -> speech -> transcription -> memory -> tool/plugin decision -> LLM -> Kokoro TTS`)
  - Tool registration, parameter validation, and AST calculator / restricted OS execution
  - Memory persistence, corruption recovery, and bounded prompt injection

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
