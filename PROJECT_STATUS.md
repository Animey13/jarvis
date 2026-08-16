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
│       SpeechManager       │ │ JarvisCore │ │   MemoryManager   │
│   (Formal State Machine:  │ │ (app/core) │ │ (Short/Persistent)│
│  WAKING, LISTENING, etc.) │ └─────┬──────┘ └───────────────────┘
└───────────────────────────┘       │
                                    ▼
                             ┌──────────────┐
                             │ ToolRegistry │
                             │  (tools/)    │
                             └──────┬───────┘
                                    │
                                    ▼
                             ┌──────────────┐
                             │ OllamaClient │
                             └──────────────┘
```

---

## 📦 Core Subsystems & Directory Tree

- **`app/`**: Core lifecycle controller, intelligence orchestrator, and console formatting (`assistant.py`, `core.py`, `logging_config.py`).
- **`config/`**: Cascading YAML and environment-overridden configuration manager (`config.py`, `settings.yaml`).
- **`speech/`**: Speech recognition, wake-word spotting, sounddevice stream captures, state machine orchestration, and neural speech synthesis (`interfaces.py`, `microphone.py`, `recognizer.py`, `wakeword.py`, `synthesizer.py`, `manager.py`).
- **`llm/`**: Async client wrapper for local language models (`base.py`, `ollama.py`).
- **`memory/`**: Short-term and persistent memory management layer (`base.py`, `local_json.py`, `manager.py`).
- **`tools/`**: Local extensible OS, status, and memory tools registry (`base.py`, `registry.py`, `system_tools.py`).
- **`tests/`**: Full pytest coverage (`test_assistant.py`, `test_intelligence_layer.py`, `test_memory_system.py`, `test_state_machine.py`, `test_tools.py`, `test_llm.py`, `test_speech.py`, `test_speech_transition.py`, `test_microphone_format.py`, etc.).

---

## 🏁 Completed Capabilities

- **Phase 1: Foundation**: Unified CLI shell (`main.py`), cascading YAML/environment settings, dual logging, and SIGINT graceful shutdown handling.
- **Phase 2: Core Intelligence & LLM Orchestration**:
  - Implemented `JarvisCore` (`app/core.py`) as the dedicated intelligence orchestrator between speech recognition and speech synthesis.
  - Maintains bounded conversation context memory with configurable `max_context_length` to prevent memory overflow.
  - Formats context prompts with explicit JARVIS system persona rules.
  - Non-blocking asynchronous LLM requests with fail-safe spoken fallbacks.
- **Phase 3: Tool & Action Execution System**:
  - Modular `BaseTool` interface with parameter schema definition (`parameters`).
  - Thread-safe `ToolRegistry` (`tools/registry.py`) providing tool discovery, lookup, argument validation (`validate_arguments`), structured logging, and structured error output wrappers (`status: success`, `status: error`).
  - Safe local tools: `DateTimeTool`, `CalculatorTool`, `SystemStatusTool`, `ListFilesTool`, `ReadFileTool`, `RestrictedCommandTool`.
- **Phase 4: Memory System**:
  - Implemented `MemoryManager` (`memory/manager.py`) coordinating Short-Term Memory (bounded in-session conversation turns) and Persistent Memory (disk-backed JSON fact store at `logs/persistent_memory.json`).
  - Supports persistent memory operations: `remember(key, value)`, `retrieve(query, limit)`, `forget(key)`, `list_memory()`, and `clear_memory()`.
  - Intentional memory creation surviving system reloads with timestamping, metadata, and automatic recovery from corrupted JSON files without crashing JARVIS.
  - Explicit memory tools in `tools/system_tools.py`: `RememberTool`, `QueryMemoryTool`, `ForgetMemoryTool`.
- **Phase 5: Natural Voice Interaction**:
  - Formalized state machine in `speech/manager.py` using `SpeechState` Enum (`WAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, `ERROR`, `SHUTDOWN`).
  - Deterministic state transitions with explicit logging (`transition_to`).
  - Mid-speech interruption handling: detecting voice activity during TTS playback transitions `SPEAKING -> INTERRUPTED -> LISTENING`, halts playback, flushes audio queues, and captures new commands.
  - Configurable timeouts (`listening_timeout`, `silence_timeout`, `maximum_command_duration`, `interruption_sensitivity`).
  - Shutdown sequence cancels microphone capture, VAD loops, STT transcription, LLM generation, and TTS tasks cleanly without orphan processes.

---

## ✅ Runtime Verification & Test Status

- 62 passing automated unit and integration tests across 12 test modules covering:
  - Formal state transitions and state transition logging
  - Interruption handling (`SPEAKING -> INTERRUPTED -> LISTENING`)
  - Queue flushing and stale frame prevention
  - Shutdown task cancellation and clean resource teardown
  - Memory persistence, tools, and core intelligence orchestration
- Validated end-to-end voice loop integration via `JarvisAssistant` and `SpeechManager`.

---

## 🔮 Remaining Priorities & Next Steps

1. **Phase 6: Custom Plugins & External Web APIs**.
2. **Phase 7: Modular Graphical User Interface & Web Dashboard**.

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
