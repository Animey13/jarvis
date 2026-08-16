# JARVIS - Project Status & Architecture Documentation

This document maintains the high-level roadmap, architecture layout, and milestone completions for **JARVIS**, a production-grade, local, offline-capable AI Assistant.

---

## 🚀 Architectural Blueprint

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
│       SpeechManager       │ │ JarvisCore │ │Memory Layer       │
│  (webrtcvad, sounddevice, │ │ (app/core) │ │(LocalJSONMemory)  │
│   faster-whisper, Kokoro) │ └─────┬──────┘ └───────────────────┘
└───────────────────────────┘       │
                                    ▼
                             ┌──────────────┐
                             │ OllamaClient │
                             └──────────────┘
```

---

## 📦 Core Subsystems & Directory Tree

- **`app/`**: Core lifecycle controller, intelligence orchestrator, and console formatting (`assistant.py`, `core.py`, `logging_config.py`).
- **`config/`**: Cascading YAML and environment-overridden configuration manager (`config.py`, `settings.yaml`).
- **`speech/`**: Speech recognition, wake-word spotting, sounddevice stream captures, and neural speech synthesis (`interfaces.py`, `microphone.py`, `recognizer.py`, `wakeword.py`, `synthesizer.py`, `manager.py`).
- **`llm/`**: Async client wrapper for local language models (`base.py`, `ollama.py`).
- **`memory/`**: Episodic chat histories persistence layer (`local_json.py`).
- **`tools/`**: Local extensible OS and status tools registry (`base.py`, `registry.py`, `system_tools.py`).
- **`tests/`**: Full pytest coverage (`test_assistant.py`, `test_intelligence_layer.py`, `test_llm.py`, `test_speech.py`, `test_speech_transition.py`, `test_microphone_format.py`, etc.).

---

## 🏁 Completed Capabilities

- **Phase 1: Foundation**: Unified CLI shell (`main.py`), cascading YAML/environment settings, dual logging, and SIGINT graceful shutdown handling.
- **Phase 2: Core Intelligence & LLM Orchestration**:
  - Implemented `JarvisCore` (`app/core.py`) as the dedicated intelligence orchestrator between speech recognition and speech synthesis.
  - Maintains bounded conversation context memory with configurable `max_context_length` to prevent memory overflow.
  - Formats context prompts with explicit JARVIS system persona rules (short, concise, natural spoken responses, no markdown/verbose fluff).
  - Queries local Ollama model asynchronously without blocking event loops.
  - Traps all LLM failures (timeouts, network errors, malformed/empty responses) and returns short spoken fallback responses.
  - Tracks and logs received commands, request start/completion metrics, latency, failures, and generated responses.
  - Integrated directly into `SpeechManager` voice callbacks for the complete runtime execution path: **Wake Word → Listen → Transcribe → LLM → Synthesize → Play**.

---

## ✅ Runtime Verification & Diagnostics

- Verified full intelligence layer test coverage (`tests/test_intelligence_layer.py`) testing normal completions, empty user inputs, LLM timeout fallbacks, network errors, empty responses, and context bounding limits.
- Validated end-to-end voice loop integration via `JarvisAssistant` and `SpeechManager`.

---

## 🔮 Remaining Priorities & Next Steps

1. **Phase 3: Extended Tool Calling & System Automation** (e.g. enhanced system diagnostics, local file searching, terminal actions).
2. **Phase 4: Memory Persistence & Knowledge Graphs**.
3. **Phase 5: Graphical User Interface & Web Dashboard**.

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
