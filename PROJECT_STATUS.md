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

## 🏁 Completed Capabilities

- **Phase 1: Foundation**: Unified CLI shell (`main.py`), cascading YAML/environment settings, dual logging, and SIGINT graceful shutdown handling.
- **Phase 2: Core Intelligence & LLM Orchestration**:
  - Implemented `JarvisCore` (`app/core.py`) as the dedicated intelligence orchestrator between speech recognition and speech synthesis.
  - Maintains bounded conversation context memory with configurable `max_context_length`.
  - Formats context prompts with explicit JARVIS system persona rules.
  - Non-blocking asynchronous LLM requests with fail-safe spoken fallbacks.
- **Phase 3: Tool & Action Execution System**:
  - Modular `BaseTool` interface with parameter schema definition (`parameters`).
  - Thread-safe `ToolRegistry` (`tools/registry.py`) providing tool discovery, lookup, argument validation (`validate_arguments`), structured logging, and structured error output wrappers (`status: success`, `status: error`).
  - Safe local tools: `DateTimeTool`, `CalculatorTool`, `SystemStatusTool`, `ListFilesTool`, `ReadFileTool`, `RestrictedCommandTool`.
- **Phase 4: Memory System**:
  - Implemented `MemoryManager` (`memory/manager.py`) coordinating Short-Term Memory (bounded in-session conversation turns) and Persistent Memory (disk-backed JSON fact store at `logs/persistent_memory.json`).
  - Supports persistent memory operations: `remember(key, value)`, `retrieve(query, limit)`, `forget(key)`, `list_memory()`, and `clear_memory()`.
  - Automatic corrupted JSON recovery without crashing JARVIS.
  - Explicit memory tools in `tools/system_tools.py`: `RememberTool`, `QueryMemoryTool`, `ForgetMemoryTool`.
- **Phase 5: Natural Voice Interaction**:
  - Formalized state machine in `speech/manager.py` using `SpeechState` Enum (`WAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, `ERROR`, `SHUTDOWN`).
  - Deterministic state transitions with explicit logging (`transition_to`).
  - Mid-speech interruption handling (`SPEAKING -> INTERRUPTED -> LISTENING`), halting playback, flushing audio queues, and capturing new commands immediately.
  - Configurable timeouts (`listening_timeout`, `silence_timeout`, `maximum_command_duration`, `interruption_sensitivity`).
- **Phase 6: Complete System Integration**:
  - Seamlessly unified all 5 subsystems into a single coherent JARVIS runtime: **Microphone → Audio Capture → VAD → Wake Word → Listening → Faster-Whisper → JARVIS Core → Memory Retrieval → Tool Decision → Tool Execution → LLM Response → Kokoro TTS → Playback → Interruption Handling → Return to WAKING**.
  - Verified dependency initialization and shutdown lifecycle order.
  - Non-blocking asyncio execution with task cancellation and zero orphaned background processes.

---

## ✅ Runtime Verification & Test Status

- 65 passing automated unit and integration tests across 13 test modules covering:
  - Complete system pipeline integration (`wake -> speech -> transcription -> memory -> tool decision -> LLM -> Kokoro TTS`)
  - State machine transitions, interruption sequences, and task cancellations
  - Tool registration, parameter validation, and AST calculator / restricted OS execution
  - Memory persistence, corruption recovery, and bounded prompt injection
  - Microphone format conversion (float32 to PCM16 mono) and ALSA default device handling
- Validated end-to-end voice loop integration via `JarvisAssistant` and `SpeechManager`.

---

## 🔮 Remaining Priorities & Next Steps

1. **Phase 7: Custom Plugins & External Web APIs**.
2. **Phase 8: Modular Graphical User Interface & Web Dashboard**.

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
