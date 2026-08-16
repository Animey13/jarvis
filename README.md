# JARVIS: Local AI Assistant Platform

JARVIS is a production-grade, offline-first local AI assistant platform designed for **Ubuntu 24.04+** and **Python 3.12+**. Built with a modular Clean Architecture, JARVIS provides real-time voice activation, local speech recognition (Faster Whisper), neural speech synthesis (Kokoro ONNX), local LLM orchestration (Ollama), bounded persistent memory, and safe local tool execution.

```
      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
      ██║███████║██████╔╝██║   ██║██║███████╗
 ██   ██║██╔══██║██╔══██║╚██╗ ██╔╝██║╚════██║
 ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

---

## 🏛️ Architecture & System Blueprint

JARVIS complies strictly with **Clean Architecture** and **SOLID** principles, utilizing asynchronous Python (`asyncio`) to coordinate all voice, memory, tool, and LLM subsystems without blocking execution.

```
                               ┌──────────────────────────┐
                               │       main.py (CLI)      │
                               └────────────┬─────────────┘
                                            │
                                            ▼
                               ┌──────────────────────────┐
                               │  JarvisAssistant (App)   │
                               └─────┬──────────────┬─────┘
                                     │              │
                                     ▼              ▼
            ┌───────────────────────────┐  ┌──────────────────┐
            │       SpeechManager       │  │    JarvisCore    │
            │   (Formal State Machine)  │  │   (app/core.py)  │
            └─────────────┬─────────────┘  └────────┬─────────┘
                          │                         │
                          ▼                         ▼
            ┌───────────────────────────┐  ┌──────────────────┐
            │   Audio Capture (ALSA)    │  │  MemoryManager   │
            │   WebRTC VAD -> Whisper   │  │ (Short/Persist)  │
            │   Kokoro ONNX Synthesis   │  └──────────────────┘
            └───────────────────────────┘           │
                                                    ▼
                                           ┌──────────────────┐
                                           │   ToolRegistry   │
                                           │    (tools/)      │
                                           └────────┬─────────┘
                                                    │
                                                    ▼
                                           ┌──────────────────┐
                                           │   OllamaClient   │
                                           └──────────────────┘
```

---

## ✨ Features

- **Continuous Voice Interaction State Machine**: Formal state loop (`WAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, `ERROR`, `SHUTDOWN`) with transition logging and deterministic state flow.
- **Mid-Speech Voice Interruption**: Speak at any time while JARVIS is responding; playback immediately halts, audio queues flush, and your new command is captured.
- **Hardware-Resilient Microphone Capture**: Auto-configures PortAudio/sounddevice to target system default ALSA inputs using native `float32` capture, automatically handling sample rate downsampling and clipping guards to deliver pristine 16 kHz mono PCM bytes to Whisper.
- **Local Neural Speech Synthesis (Kokoro ONNX)**: Ultra-realistic local voice generation (default `af_sky` voice) executing ONNX models with zero cloud latency.
- **Local Asynchronous LLM Orchestration**: Non-blocking `OllamaClient` communicating over local HTTP REST endpoints, featuring fail-safe spoken fallbacks.
- **Dual Memory Subsystem**: Bounded short-term in-session conversation history paired with persistent, disk-backed JSON fact storage (`logs/persistent_memory.json`) featuring auto-recovery from corrupted files.
- **Extensible Safe Tool Calling**: `ToolRegistry` supporting parameter schema validation and execution of safe local tools (calculator, system diagnostics, timezone date/time, file operations, allowlisted commands).

---

## 🛠️ Technology Stack

| Category | Component / Library | Description |
| :--- | :--- | :--- |
| **Language & Concurrency** | Python 3.12+, `asyncio` | Asynchronous non-blocking runtime event loop |
| **CLI & UI** | `typer`, `rich` | Terminal rendering, banners, and structured commands |
| **Configuration** | `PyYAML`, `python-dotenv` | Cascading YAML & environment variable parser |
| **Speech-to-Text (STT)** | `faster-whisper`, `webrtcvad` | Offline Whisper CTranslate2 engine with WebRTC VAD |
| **Text-to-Speech (TTS)** | `kokoro-onnx`, `soundfile` | High-fidelity local ONNX neural voice generator |
| **LLM Inference** | `ollama`, `httpx` | Local offline Llama 3 / Ollama REST client |
| **Testing** | `pytest`, `pytest-asyncio` | 100% automated test coverage across 13 test modules |

---

## ⚙️ Installation & Setup

### 1. System Dependencies (Ubuntu 24.04+)

Ensure Python 3.12+ and system audio utilities are installed:
```bash
sudo apt update
sudo apt install -y python3-pip python3-venv portaudio19-dev pulseaudio-utils alsa-utils
```

### 2. Environment Setup

Clone the repository and set up a virtual environment:
```bash
git clone https://github.com/your-username/jarvis.git
cd jarvis

python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

---

## 🦙 Ollama Setup & Model Configuration

JARVIS utilizes **Ollama** for completely local LLM inference.

1. **Install Ollama on Ubuntu**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```
2. **Pull the Llama 3 model**:
   ```bash
   ollama pull llama3:8b
   ```
3. **Verify local server status**:
   ```bash
   curl http://localhost:11434/api/tags
   ```

---

## 🎙️ Microphone & Audio Requirements

- **Input Format**: JARVIS captures 16 kHz mono audio for Whisper.
- **Device Selection**: Configured to use the OS `"default"` ALSA device (`microphone.device: "default"` in `config/settings.yaml`).
- **Resampling**: If your microphone hardware only supports 44.1 kHz or 48 kHz natively, JARVIS automatically resamples incoming audio frames in real time.

---

## 🚀 Running JARVIS

JARVIS exposes an interactive CLI using `typer`:

```bash
# Start JARVIS Voice & CLI Assistant
python main.py start

# Display current system configurations
python main.py config

# Display release and platform versions
python main.py version

# Test TTS synthesis independently
python main.py test-tts

# Test microphone recording and STT independently
python main.py test-mic
```

---

## 🔄 Voice Interaction Flow

```
1. Speak 'Jarvis' (WAKING state)
   └─► VAD detects speech -> Wake word identified
2. Transition to LISTENING state
   └─► Console displays: 🎙️ [Wake Word] 'Jarvis' detected! Listening...
3. Speak your command (e.g. "What time is it?")
   └─► Silence detected -> Transition to TRANSCRIBING
4. Faster Whisper yields transcript: "What time is it?"
   └─► Transition to THINKING -> JarvisCore evaluates context & tools
5. Tool decision triggered -> DateTimeTool executes
   └─► Real-time date/time output passed to Ollama for response synthesis
6. Transition to SPEAKING state
   └─► Kokoro ONNX speaks synthesized response
7. User Interruption (Optional)
   └─► Speak mid-response -> Transition SPEAKING -> INTERRUPTED -> LISTENING
8. Return to WAKING state
```

---

## 🛠️ Available Local Tools

JARVIS includes a suite of safe, extensible local tools:

| Tool Name | Command Tag | Description |
| :--- | :--- | :--- |
| **DateTimeTool** | `[TOOL: get_current_datetime]` | Retrieves timezone-aware date, time, and weekday |
| **CalculatorTool** | `[TOOL: calculator, expression='12 * 4']` | Safely evaluates math expressions via AST parsing |
| **SystemStatusTool** | `[TOOL: get_system_status]` | Queries CPU load, RAM, disk usage, and system uptime |
| **ListFilesTool** | `[TOOL: list_files, path='.']` | Safely lists directory contents and file sizes |
| **ReadFileTool** | `[TOOL: read_file, filepath='file.txt']` | Reads small text files safely (10KB limit) |
| **RestrictedCommandTool** | `[TOOL: restricted_command, command='uptime']` | Executes allowlisted OS commands (`uptime`, `df`, `free`, `whoami`) |
| **RememberTool** | `[TOOL: remember_fact, key='k', value='v']` | Saves intentional facts to persistent memory |
| **QueryMemoryTool** | `[TOOL: query_memory, query='k']` | Searches stored persistent facts |
| **ForgetMemoryTool** | `[TOOL: forget_fact, key='k']` | Deletes stored facts from memory |

---

## 🧠 Memory System

JARVIS features a two-tier memory system:
1. **Short-Term Memory**: Bounded in-session conversation history (`max_context_length` in settings) preventing unbounded prompt memory growth.
2. **Persistent Memory**: Disk-backed JSON fact store (`logs/persistent_memory.json`) storing intentional facts and preferences across restarts, featuring automatic corrupted JSON recovery.

---

## 📂 Project Structure

```
jarvis/
├── app/
│   ├── assistant.py          # Central JarvisAssistant application lifecycle controller
│   ├── core.py               # JarvisCore intelligence & LLM/Memory/Tool orchestrator
│   └── logging_config.py     # Global Rich console & rotating file logging configuration
├── assets/                   # Local Kokoro ONNX model weights and voice assets
├── config/
│   ├── config.py             # Cascading PyYAML and environment settings loader
│   └── settings.yaml         # Default system configurations
├── docs/
│   └── architecture.md       # In-depth system design documentation
├── llm/
│   ├── base.py               # Abstract BaseLLMClient interface
│   └── ollama.py             # Async httpx Ollama client wrapper
├── logs/                     # Application runtime logs and persistent memory storage
├── memory/
│   ├── base.py               # Abstract BaseMemory interface
│   ├── local_json.py         # Local JSON episodic memory driver
│   └── manager.py            # MemoryManager short-term & persistent memory manager
├── speech/
│   ├── interfaces.py         # Abstract AudioInput, SpeechRecognizer, SpeechSynthesizer interfaces
│   ├── manager.py            # SpeechManager formal state machine & state transitions
│   ├── microphone.py         # Hardware sounddevice capture, ALSA default mapping & resampler
│   ├── recognizer.py         # Faster-Whisper STT with WebRTC VAD and signal diagnostics
│   ├── synthesizer.py        # Kokoro ONNX neural speech synthesizer with Piper fallback
│   └── wakeword.py           # Custom wake-word engine and gating rules
├── tests/                    # 100% passing automated test suite (65 tests across 13 modules)
├── tools/
│   ├── base.py               # Abstract BaseTool interface with input parameter schemas
│   ├── registry.py           # Thread-safe ToolRegistry with validation & structured logging
│   └── system_tools.py       # Safe local tools (math, datetime, system, files, memory)
├── .env.example              # Environment variables template
├── main.py                   # Core CLI entry point (Typer)
├── PROJECT_STATUS.md         # Comprehensive project roadmap & completion status
└── requirements.txt          # System Python dependencies
```

---

## ❓ Troubleshooting

| Issue | Solution |
| :--- | :--- |
| **PortAudio library not found** | Install `portaudio19-dev` using `sudo apt install -y portaudio19-dev`. JARVIS will fall back to virtual simulation mode automatically if hardware is missing. |
| **Ollama Connection Error** | Ensure Ollama server is running locally via `ollama serve` and that `llama3:8b` model is pulled (`ollama pull llama3:8b`). |
| **TTS Assets Missing** | Verify that `kokoro-v1.0.fp16.onnx` and `voices-v1.0.bin` are located inside `assets/`. JARVIS displays a subtitle warning if models are missing. |

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:
```bash
pytest -v
```
