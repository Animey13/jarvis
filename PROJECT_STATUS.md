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
│       SpeechManager       │ │LLM Client  │ │Memory Layer       │
│  (webrtcvad, sounddevice, │ │(Ollama)    │ │(LocalJSONMemory)  │
│   faster-whisper, Kokoro) │ └────────────┘ └───────────────────┘
└───────────────────────────┘
                         │
                         ▼
┌───────────────────────────┐
│       ToolRegistry        │
│   (DateTime / SysStatus)  │
└───────────────────────────┘
```

---

## 📦 Core Subsystems & Directory Tree

- **`app/`**: Core lifecycle controller, console formatting, and orchestrator (`assistant.py`, `logging_config.py`).
- **`config/`**: Cascading YAML and environment-overridden configuration manager (`config.py`, `settings.yaml`).
- **`speech/`**: Speech recognition, wake-word spotting, sounddevice stream captures, and neural speech synthesis (`interfaces.py`, `microphone.py`, `recognizer.py`, `wakeword.py`, `synthesizer.py`, `manager.py`).
- **`llm/`**: Async client wrapper for local language models (`ollama.py`).
- **`memory/`**: Episodic chat histories persistence layer (`local_json.py`).
- **`tools/`**: Local extensible OS and status tools registry (`base.py`, `registry.py`, `system_tools.py`).
- **`tests/`**: Full pytest coverage (`test_assistant.py`, `test_tools.py`, `test_speech.py`, etc.).

---

## 🏁 Completed Capabilities

- **Unified CLI shell & cascading configurations**: Fully asynchronous terminal UI supporting configuration displays and SIGINT handling.
- **Offline Echo-Compensated Audio Pipeline**: Integrated VAD and whisper transcription with audio hardware simulators and neural speech synthesis via **Kokoro**.
- **Asynchronous LLM Client**: Non-blocking `OllamaClient` supporting asynchronous generation, streaming, and offline-failback mechanisms.
- **Episodic JSON Memory**: Automated history loading, context windowing, serialization, and context injection.
- **Dynamic Local Tool Calling**: Extensible `ToolRegistry` with pattern matching for custom bracket-enclosed tags. Includes timezone-aware date/time tracking and local Linux system metrics gathering (`DateTimeTool`, `SystemStatusTool`).

---

## ✅ Runtime Verification & Fixes

We performed a real end-to-end runtime verification of the integrated tool-calling subsystem using the primary application entry point (`python3 main.py start`), routing live interactive sessions through a local mock LLM server.

### **Tests Performed & Results:**
1. **Conversational request without tools**: Inputs like `"Hello"` were processed natively without trigger calls, receiving a standard conversational response.
2. **DateTimeTool execution**: Asking `"What time is it?"` triggered the `get_current_datetime` tool tag, executed the tool successfully, and injected the timestamp back to the LLM.
3. **SystemStatusTool execution**: Asking `"Check my system status"` triggered the `get_system_status` tool tag, extracted CPU, memory, and disk diagnostics, and synthesized a natural summary response.
4. **Invalid tool handling**: Simulating an unsupported tool tag failed gracefully; the `ToolRegistry` caught the error and presented a polite response without crashing the application.
5. **Conversational memory updates**: Validated that `logs/memory.json` correctly captured and serialized all turns with appropriate timestamps and roles.

### **Fixes & Enhancements Made:**
- Resolved a prompt-matching edge case in the simulation environment where conversational history keywords could trigger false-positive tool calls, ensuring that matching behaves identically to Llama 3 models.

---

## 🔮 Remaining Priorities & Next Steps

1. **Phase 6: Custom Plugins & External Web APIs** (e.g., local home automation, offline web scraper, or open weather tools).
2. **Phase 7: Modular Graphical User Interface** (e.g., standard text/voice UI dashboard or rich web front-end client).

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
