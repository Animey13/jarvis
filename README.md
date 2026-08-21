# JARVIS: Local AI Assistant Platform

JARVIS is a production-grade, offline-first local AI assistant platform designed for **Ubuntu 24.04+** and **Python 3.12+**. Built with a modular Clean Architecture, JARVIS provides real-time voice activation, local speech recognition (Faster Whisper), neural speech synthesis (Kokoro ONNX), local LLM orchestration (Ollama), custom plugin architecture, bounded persistent memory, safe local tool execution, and an interactive local **Web Dashboard** (FastAPI + WebSockets).

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

JARVIS complies strictly with **Clean Architecture** and **SOLID** principles, utilizing asynchronous Python (`asyncio`) to coordinate all voice, memory, tool, plugin, LLM, and web dashboard subsystems without blocking execution.

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
            │   Audio Capture (ALSA)    │  │  PluginManager   │
            │   WebRTC VAD -> Whisper   │  │  (plugins/)      │
            │   Kokoro ONNX Synthesis   │  └────────┬─────────┘
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

- **Custom Plugin Architecture & API Integrations**: Modular plugin infrastructure (`BasePlugin`, `PluginRegistry`, `PluginManager`) with explicit permission levels (`READ_ONLY`, `NETWORK`, `FILESYSTEM`, `SYSTEM`, `EXECUTION`), failure isolation, tool bridging, and graceful offline degradation.
- **Built-in Plugins**: Includes `SystemPlugin` (diagnostics, datetime, file operations, math), `WeatherPlugin` (location forecasts via Open-Meteo with offline fallbacks), and `WebSearchPlugin` (provider-agnostic search engine via DuckDuckGo with offline fallbacks).
- **Interactive Local Web Dashboard (FastAPI + WebSockets)**: Real-time graphical user interface displaying voice interaction state, scrolling live event feeds, conversation log, plugins management, registered tools, persistent memory management, and system diagnostics.
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
| **Plugins Infrastructure** | `BasePlugin`, `PluginRegistry`, `PluginManager` | Dynamic loading, permission safety, tool bridging |
| **Web Server & API** | `fastapi`, `uvicorn`, `pydantic` | Local REST API and WebSocket real-time server |
| **CLI & UI** | `typer`, `rich` | Terminal rendering, banners, and structured commands |
| **Frontend** | HTML5, CSS3, Vanilla JS | Offline-first dark terminal theme dashboard (zero CDNs) |
| **Configuration** | `PyYAML`, `python-dotenv` | Cascading YAML & environment variable parser |
| **Speech-to-Text (STT)** | `faster-whisper`, `webrtcvad` | Offline Whisper CTranslate2 engine with WebRTC VAD |
| **Text-to-Speech (TTS)** | `kokoro-onnx`, `soundfile` | High-fidelity local ONNX neural voice generator |
| **LLM Inference** | `ollama`, `httpx` | Local offline Llama 3 / Ollama REST client |
| **Testing** | `pytest`, `pytest-asyncio` | 100% automated test coverage across 16 test modules (81 tests) |

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

## 🧩 Plugin System & Developer Guide

### Creating a Custom Plugin

Plugins inherit from `BasePlugin` and declare metadata, permissions, and tools:

```python
from typing import Any, Dict, List
from plugins.base import BasePlugin, PluginToolBridge
from plugins.permissions import PluginPermission
from plugins.schemas import PluginMetadata

class CustomPlugin(BasePlugin):
    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="custom_plugin",
            version="1.0.0",
            description="Custom capability plugin",
            capabilities=["my_capability"],
            permissions=[PluginPermission.READ_ONLY],
        )

    def get_tools(self) -> List[Any]:
        return [
            PluginToolBridge(
                plugin=self,
                tool_name="my_capability",
                description="Executes custom capability.",
                parameters={"param": {"type": "string", "required": True}},
            )
        ]

    async def execute(self, capability: str, **kwargs: Any) -> Any:
        if capability == "my_capability":
            return {"result": f"Executed with {kwargs.get('param')}"}
        raise ValueError(f"Unknown capability {capability}")
```

### Plugin Configuration in `config/settings.yaml`:
```yaml
plugins:
  enabled: true
  weather:
    enabled: true
  web_search:
    enabled: true
  system:
    enabled: true
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

---

## 🌐 REST API & WebSocket Specifications

### REST Endpoints
- `GET /api/status`: Returns subsystem statuses, current state, and uptime.
- `GET /api/config`: Returns sanitized configuration settings.
- `GET /api/plugins`: Returns registered plugins and statuses.
- `GET /api/plugins/{name}`: Returns detailed status for a plugin.
- `POST /api/plugins/{name}/enable`: Enables a plugin.
- `POST /api/plugins/{name}/disable`: Disables a plugin.
- `GET /api/tools`: Lists registered tools, parameter schemas, and tool execution logs.
- `GET /api/memory`: Returns persistent and short-term memory stats.
- `POST /api/memory`: Stores a fact into persistent memory (`{"key": "name", "value": "Alex"}`).
- `DELETE /api/memory/{key}`: Removes a fact from persistent memory.
- `POST /api/chat`: Text prompt query endpoint (`{"message": "Hello JARVIS"}`).
- `GET /api/system`: Returns CPU, RAM, disk metrics, and Ollama status.
- `POST /api/control`: Runtime controls (`{"action": "start"}` or `{"action": "stop"}`).
- `GET /api/events`: Returns recent event log history feed.

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:
```bash
pytest -v
```
