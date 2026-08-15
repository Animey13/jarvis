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
- **`tests/`**: Full pytest coverage (`test_assistant.py`, `test_tools.py`, `test_speech.py`, `test_speech_transition.py`, `test_microphone_format.py`, etc.).

---

## 🏁 Completed Capabilities

- **Unified CLI shell & cascading configurations**: Fully asynchronous terminal UI supporting configuration displays and SIGINT handling.
- **Offline Echo-Compensated Audio Pipeline**: Integrated VAD and whisper transcription with audio hardware simulators and neural speech synthesis via **Kokoro**.
- **Resilient Default OS Microphone Integration**: Targets virtual ALSA `"default"` device using `"float32"` natively, performing automatic hardware rate resampling and translation to mono 16-bit PCM.
- **VAD-Gated Wake-Word State Machine**: Resolved logic reversal in `SpeechManager` `WAKING` state so that voice activity (`recent_activity_count > 0`) triggers rolling wake-buffer transcription checks rather than suppressing them.
- **Instant Non-Blocking Wake-Word Transition**: Optimized state machine to instantly enter `LISTENING` mode upon wake-word detection ("Jarvis") without blocking audio capture on speaker playback.
- **STT Signal Diagnostics & Debug WAV Dump**: Implemented diagnostic logging in `speech/recognizer.py` calculating PCM signal stats (len_bytes, shape, dtype, duration, min, max, RMS, peak) and writing post-wake audio buffers to `/tmp/jarvis-debug-command.wav`.
- **Asynchronous LLM Client**: Non-blocking `OllamaClient` supporting asynchronous generation, streaming, and offline-failback mechanisms.
- **Episodic JSON Memory**: Automated history loading, context windowing, serialization, and context injection.
- **Dynamic Local Tool Calling**: Extensible `ToolRegistry` with pattern matching for custom bracket-enclosed tags (`DateTimeTool`, `SystemStatusTool`).

---

## ✅ Runtime Verification & Fixes

### **Wake-Word State Machine Logic Fix**:
- **Root Cause Identified**: In `speech/manager.py`, wake-word candidate transcription was gated by `recent_activity_count == 0`, which required silence before checking for "Jarvis". This inverted VAD logic because saying "Jarvis" produced voice activity (`recent_activity_count > 0`), causing wake-word detection to be skipped.
- **Behavioral Fix**: Corrected condition to `recent_activity_count > 0`, ensuring that voice activity triggers wake-word transcription. Implemented a sliding window buffer (`del rolling_wake_buffer[:10]`) so rolling audio is checked continuously without transcribing pure silence. Added clear logging: `logger.info("Wake word candidate text: '%s' (Confidence: %.2f)", transcription.text, transcription.confidence)`.

### **End-to-End Test Results**:
1. **Wake Word Detection**: Successfully detected `"Jarvis"` during voice activity.
2. **Console UI Indicator**: Printed `🎙️ [Wake Word] 'Jarvis' detected! Listening...`
3. **Command Capture**: Captures post-wake audio and yields exact Whisper transcript `"Hello Jarvis"`.
4. **Orchestrator Routing**: Transcript reaches `JarvisAssistant` and queries local Ollama model.
5. **LLM Synthesis & Speech Output**: Response generated by LLM is synthesized and spoken aloud by Kokoro.

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
