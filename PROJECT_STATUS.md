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

## 🏁 Completed Milestones

### **Phase 1: Foundation (Completed)**
- Integrated cascading YAML-based configurations and unified logging formats.
- Structured asymmetric OS signal traps to support graceful system shutdowns on Ubuntu 24.04+.

### **Phase 2: Speech Layer (Completed & Echo-Compensated)**
- Integrated SoundDevice PCM streaming with simulated virtual queue fallbacks.
- Integrated WebRTC-based Voice Activity Detection (VAD) and offline STT via Faster-Whisper.
- Integrated **Kokoro ONNX neural speech synthesis** as the primary high-fidelity voice generator.
- Implemented state-machine transition flushes to solve wake-word-echo audio loop triggers.

### **Phase 3: LLM Integration (Completed)**
- Built async-capable connection client to offline Ollama microservices with connection fallbacks.

### **Phase 4: Memory Layer (Completed)**
- Constructed serialized JSON local episodic memory database with dynamic contextual injection.

### **Phase 5: Tool Calling Subsystem (Completed - CURRENT)**
- Created a thread-safe extensible tool registry.
- Developed concrete Unix diagnostics and timezone-aware datetime parsing tools.
- Integrated multi-turn LLM coordination logic that detects bracket tool tags, executes them locally, and feeds back structured system variables for natural language rendering.

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
Use keyboard triggers, type query commands, or wake the voice assistant using:
- **Wake Word**: Speak `"Jarvis"` followed by your question (e.g. *"What time is it?"* or *"How is the system running?"*).
