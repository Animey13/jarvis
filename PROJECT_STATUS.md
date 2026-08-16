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
│  Audio Capture (Default)  ││ OllamaClient │
│    WebRTC VAD -> Whisper  │└──────────────┘
│    Kokoro TTS Playback    │
└───────────────────────────┘
```

---

## 📦 Core Subsystems & Directory Tree

- **`app/`**: Core lifecycle controller, intelligence orchestrator, and console formatting (`assistant.py`, `core.py`, `logging_config.py`).
- **`config/`**: Cascading YAML and environment-overridden configuration manager (`config.py`, `settings.yaml`).
- **`speech/`**: Speech recognition, wake-word spotting, sounddevice stream captures, formal state machine orchestration, and neural speech synthesis (`interfaces.py`, `microphone.py`, `recognizer.py`, `wakeword.py`, `synthesizer.py`, `manager.py`).
- **`llm/`**: Async client wrapper for local language models (`base.py`, `ollama.py`).
- **`memory/`**: Short-term and persistent memory management layer (`base.py`, `local_json.py`, `manager.py`).
- **`tools/`**: Local extensible OS, status, and memory tools registry (`base.py`, `registry.py`, `system_tools.py`).
- **`tests/`**: Full pytest coverage (`test_assistant.py`, `test_intelligence_layer.py`, `test_memory_system.py`, `test_state_machine.py`, `test_system_integration.py`, `test_tools.py`, `test_llm.py`, `test_speech.py`, `test_speech_transition.py`, `test_microphone_format.py`, etc.).

---

## 🏁 Completed Capabilities & Roadmap

- **Phase 1: Foundation (Completed)**: Unified CLI shell (`main.py`), cascading YAML/environment settings, dual logging, and SIGINT graceful shutdown handling.
- **Phase 2: Core Intelligence & LLM Orchestration (Completed)**:
  - Implemented `JarvisCore` (`app/core.py`) as the dedicated intelligence orchestrator between speech recognition and speech synthesis.
  - Maintains bounded conversation context memory with configurable `max_context_length`.
  - Formats context prompts with explicit JARVIS system persona rules.
  - Non-blocking asynchronous LLM requests with fail-safe spoken fallbacks.
- **Phase 3: Tool & Action Execution System (Completed)**:
  - Modular `BaseTool` interface with parameter schema definition (`parameters`).
  - Thread-safe `ToolRegistry` (`tools/registry.py`) providing tool discovery, lookup, argument validation (`validate_arguments`), structured logging, and structured error output wrappers (`status: success`, `status: error`).
  - Safe local tools: `DateTimeTool`, `CalculatorTool`, `SystemStatusTool`, `ListFilesTool`, `ReadFileTool`, `RestrictedCommandTool`.
- **Phase 4: Memory System (Completed)**:
  - Implemented `MemoryManager` (`memory/manager.py`) coordinating Short-Term Memory (bounded in-session conversation turns) and Persistent Memory (disk-backed JSON fact store at `logs/persistent_memory.json`).
  - Supports persistent memory operations: `remember(key, value)`, `retrieve(query, limit)`, `forget(key)`, `list_memory()`, and `clear_memory()`.
  - Automatic corrupted JSON recovery without crashing JARVIS.
  - Explicit memory tools in `tools/system_tools.py`: `RememberTool`, `QueryMemoryTool`, `ForgetMemoryTool`.
- **Phase 5: Natural Voice Interaction (Completed)**:
  - Formalized state machine in `speech/manager.py` using `SpeechState` Enum (`WAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, `ERROR`, `SHUTDOWN`).
  - Deterministic state transitions with explicit logging (`transition_to`).
  - Mid-speech interruption handling (`SPEAKING -> INTERRUPTED -> LISTENING`), halting playback, flushing audio queues, and capturing new commands immediately.
  - Configurable timeouts (`listening_timeout`, `silence_timeout`, `maximum_command_duration`, `interruption_sensitivity`).
- **Phase 6: Complete System Integration (Completed)**:
  - Seamlessly unified all subsystems into a single coherent JARVIS runtime: **Microphone → Audio Capture → VAD → Wake Word → Listening → Faster-Whisper → JARVIS Core → Memory Retrieval → Tool Decision → Tool Execution → LLM Response → Kokoro TTS → Playback → Interruption Handling → Return to WAKING**.
- **Phase 7: Product Polish & Documentation (Completed - CURRENT)**:
  - Cleaned runtime output, improved Rich console UX, clear state transition indicators, and clean user-friendly error messages.
  - Comprehensive documentation across `README.md`, `PROJECT_STATUS.md`, and `docs/architecture.md`.
  - Verified 100% clean startup and CLI interface execution.

---

## ⚠️ Known Limitations & Issues

1. **Hardware Microphone Echo Handling**: On open speaker setups without hardware echo cancellation, high speaker volume may bleed into the microphone during TTS playback. Softened via VAD sensitivity gating and interruption thresholds.
2. **Local LLM Performance**: Inference speed is dependent on local GPU/CPU availability for Ollama. Timeouts default to 30s to accommodate slower CPU-only environments.

---

## 🔮 Future Improvements

1. **Phase 8: Web Dashboard & Modular GUI**: A web-based status dashboard providing real-time audio visualization, state logs, and chat controls.
2. **Phase 9: Local Vector Embeddings (RAG)**: Integrating local vector stores (e.g. ChromaDB) for semantic file search.

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
