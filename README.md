# JARVIS: Local AI Assistant Platform

JARVIS is a production-grade, offline-first local AI assistant platform designed for **Ubuntu 24.04+** and **Python 3.12+**. Built with a modular Clean Architecture, JARVIS provides real-time voice activation, local speech recognition (Faster Whisper), neural speech synthesis (Kokoro ONNX), local LLM orchestration (Ollama), bounded persistent memory, safe local tool execution, and an interactive local **Web Dashboard** (FastAPI + WebSockets).

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

JARVIS complies strictly with **Clean Architecture** and **SOLID** principles, utilizing asynchronous Python (`asyncio`) to coordinate all voice, memory, tool, LLM, and web dashboard subsystems without blocking execution.

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

- **Interactive Local Web Dashboard (FastAPI + WebSockets)**: Real-time graphical user interface displaying voice interaction state, scrolling live event feeds, conversation log, registered tools, persistent memory management, and system diagnostics.
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
| **Web Server & API** | `fastapi`, `uvicorn`, `pydantic` | Local REST API and WebSocket real-time server |
| **CLI & UI** | `typer`, `rich` | Terminal rendering, banners, and structured commands |
| **Frontend** | HTML5, CSS3, Vanilla JS | Offline-first dark terminal theme dashboard (zero CDNs) |
| **Configuration** | `PyYAML`, `python-dotenv` | Cascading YAML & environment variable parser |
| **Speech-to-Text (STT)** | `faster-whisper`, `webrtcvad` | Offline Whisper CTranslate2 engine with WebRTC VAD |
| **Text-to-Speech (TTS)** | `kokoro-onnx`, `soundfile` | High-fidelity local ONNX neural voice generator |
| **LLM Inference** | `ollama`, `httpx` | Local offline Llama 3 / Ollama REST client |
| **Testing** | `pytest`, `pytest-asyncio` | 100% automated test coverage across 14 test modules (74 tests) |

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
git clone https://github.com/Animey13/jarvis.git
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

## 🖥️ Web Dashboard Launch & Usage

Launch the local Web Dashboard server:
```bash
# Launch Dashboard (REST & WebSockets on http://127.0.0.1:8000)
python main.py dashboard

# Launch Dashboard alongside background voice assistant loop
python main.py dashboard --with-assistant

# Specify custom host/port
python main.py dashboard --host 127.0.0.1 --port 8080
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

### Dashboard Panels & Features
1. **Header Bar**: Live WebSocket connection badge and application status dot.
2. **Voice Interaction State**: Current state display (`WAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`, etc.) with animated wave visualizer and subsystem health badges.
3. **Conversation Panel**: Interactive chat log displaying user prompts and JARVIS responses with an input box to send text queries.
4. **Live Event Stream**: Real-time scrolling feed of structured system events (`state_change`, `transcription`, `tool_start`, `tool_complete`, `memory_update`, `error`).
5. **Registered Tools**: Dynamic catalog of all registered tools with name, description, and parameter schemas.
6. **Persistent Memory**: Manage persistent facts (`remember_fact` form and `forget_fact` buttons).
7. **System Diagnostics**: Real-time CPU load, RAM usage, disk usage progress bars, uptime, Python version, and Start/Stop runtime controls.

---

## 🌐 REST API & WebSocket Specifications

### REST Endpoints
- `GET /api/status`: Returns subsystem statuses, current state, and uptime.
- `GET /api/config`: Returns sanitized configuration settings.
- `GET /api/tools`: Lists registered tools, parameter schemas, and tool execution logs.
- `GET /api/memory`: Returns persistent and short-term memory stats.
- `POST /api/memory`: Stores a fact into persistent memory (`{"key": "name", "value": "Alex"}`).
- `DELETE /api/memory/{key}`: Removes a fact from persistent memory.
- `POST /api/chat`: Text prompt query endpoint (`{"message": "Hello JARVIS"}`).
- `GET /api/system`: Returns CPU, RAM, disk metrics, and Ollama status.
- `POST /api/control`: Runtime controls (`{"action": "start"}` or `{"action": "stop"}`).
- `GET /api/events`: Returns recent event log history feed.

### WebSocket Endpoint
- `WS /ws`: Broadcasts real-time JSON event objects (`state_change`, `transcription`, `user_message`, `assistant_message`, `tool_start`, `tool_complete`, `memory_update`, `error`).

---

## 🔒 Security Model

- **Local Binding**: Binds exclusively to `127.0.0.1` by default to prevent unauthorized network access.
- **No Arbitrary Shell / File Execution**: Tool execution enforces parameter schemas, safe AST arithmetic evaluation, and strict allowlists for system commands. File reading is capped at 10KB limits.
- **Sanitized Configs**: `.env` secrets and credentials are never exposed via the Web API.

---

## 🎙️ Microphone & Audio Requirements

- **Input Format**: JARVIS captures 16 kHz mono audio for Whisper.
- **Device Selection**: Configured to use the OS `"default"` ALSA device (`microphone.device: "default"` in `config/settings.yaml`).
- **Resampling**: If your microphone hardware only supports 44.1 kHz or 48 kHz natively, JARVIS automatically resamples incoming audio frames in real time.

---

## 🚀 Running JARVIS CLI Commands

JARVIS exposes commands through `main.py` using `typer`:

```bash
# Start JARVIS Voice & CLI Assistant
python main.py start

# Launch Web Dashboard
python main.py dashboard

# Display active system configurations
python main.py config

# Display release and platform versions
python main.py version

# Test TTS synthesis independently
python main.py test-tts

# Test microphone recording and STT independently
python main.py test-mic
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
├── tests/                    # 100% passing automated test suite (74 tests across 14 modules)
├── tools/
│   ├── base.py               # Abstract BaseTool interface with input parameter schemas
│   ├── registry.py           # Thread-safe ToolRegistry with validation & structured logging
│   └── system_tools.py       # Safe local tools (math, datetime, system, files, memory)
├── web/                      # Phase 8 Web Dashboard & API Subpackage
│   ├── app.py                # FastAPI web server and WebSocket endpoint
│   ├── routes.py             # REST API router endpoints
│   ├── schemas.py            # Typed Pydantic request and response schemas
│   ├── state.py              # EventBus publisher and WebStateManager
│   ├── websocket.py          # WebSocket connection & broadcast manager
│   └── static/               # HTML5/CSS3/JS dark terminal theme dashboard assets
├── .env.example              # Environment variables template
├── main.py                   # Core CLI entry point (Typer)
├── PROJECT_STATUS.md         # Comprehensive project roadmap & completion status
└── requirements.txt          # System Python dependencies
```

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:
```bash
pytest -v
```
