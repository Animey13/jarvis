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
- **`speech/`**: Speech recognition, wake-word spotting, sounddevice stream captures, and neural speech synthesis (`interfaces.py`, `microphone.py`, `recognizer.py`, `wakeword.py`, `synthesizer.py`, `manager.py`).
- **`llm/`**: Async client wrapper for local language models (`base.py`, `ollama.py`).
- **`memory/`**: Episodic chat histories persistence layer (`local_json.py`).
- **`tools/`**: Local extensible OS and status tools registry (`base.py`, `registry.py`, `system_tools.py`).
- **`tests/`**: Full pytest coverage (`test_assistant.py`, `test_intelligence_layer.py`, `test_tools.py`, `test_llm.py`, `test_speech.py`, `test_speech_transition.py`, `test_microphone_format.py`, etc.).

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
  - Implemented initial set of SAFE LOCAL tools in `tools/system_tools.py`:
    - `DateTimeTool`: Timezone-aware date, time, and weekday tracking (`get_current_datetime`).
    - `CalculatorTool`: Safe mathematical expression evaluation using Python AST parsing (`calculator`).
    - `SystemStatusTool`: CPU load, memory, disk, and uptime metrics (`get_system_status`).
    - `ListFilesTool`: Directory listing with item bounds (`list_files`).
    - `ReadFileTool`: Safe text file content reading with 10KB size limits (`read_file`).
    - `RestrictedCommandTool`: Strictly allowlisted, non-shell OS command execution (`restricted_command` with commands like `uptime`, `whoami`, `df`, `free`, `hostname`).
  - Integrated `ToolRegistry` directly into `JarvisCore` (`app/core.py`) for automated intent decisioning, bracket tag parsing, tool execution, and natural response synthesis.

---

## ✅ Runtime Verification & Test Status

- 50 passing automated unit and integration tests across 10 test modules covering:
  - Tool registration, discovery, and lookup
  - Argument validation and parameter schema verification
  - Successful and failed tool execution
  - Malformed argument and unknown tool error handling
  - `JarvisCore` tool orchestration and response synthesis
- Validated end-to-end voice loop integration via `JarvisAssistant` and `SpeechManager`.

---

## 🔮 Remaining Priorities & Next Steps

1. **Phase 4: Memory Persistence & Knowledge Graphs**.
2. **Phase 5: Custom Plugins & External Web APIs**.
3. **Phase 6: Modular Graphical User Interface & Dashboard**.

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
