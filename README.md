# JARVIS: Local AI Assistant Platform

JARVIS is a production-grade, offline-first local AI assistant platform designed for **Ubuntu 24.04+** and **Python 3.12+**. Built with a modular Clean Architecture, JARVIS provides real-time voice activation, local speech recognition (Faster Whisper), neural speech synthesis (Kokoro ONNX), local LLM orchestration (Ollama), custom plugin architecture, local vector embeddings & RAG document search, bounded persistent memory, safe local tool execution, and an interactive local **Web Dashboard** (FastAPI + WebSockets).

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

JARVIS complies strictly with **Clean Architecture** and **SOLID** principles, utilizing asynchronous Python (`asyncio`) to coordinate all voice, memory, tool, plugin, RAG, LLM, and web dashboard subsystems without blocking execution.

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
            │   Audio Capture (ALSA)    │  │    RAGManager    │
            │   WebRTC VAD -> Whisper   │  │    (rag/)        │
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

## 🎭 End-to-End Demonstration Workflow

Follow this demonstration workflow to exercise all JARVIS subsystems end-to-end:

### A. Start Dashboard & Voice Assistant
```bash
# Launch Web Dashboard alongside background assistant loop
python main.py dashboard --with-assistant
```
Open browser at `http://127.0.0.1:8000`.

### B. Ask a General Question
- **Voice Input**: *"Jarvis, what is the capital of France?"*
- **Pipeline**: Whisper -> JarvisCore -> Ollama (Llama3) -> Kokoro TTS.

### C. Ask a System Question
- **Voice Input**: *"Jarvis, how is the system running?"*
- **Pipeline**: Whisper -> JarvisCore -> `SystemStatusTool` -> LLM Synthesis -> Kokoro TTS.

### D. Ask a Weather Question
- **Voice Input**: *"Jarvis, what's the weather in Jaipur?"*
- **Pipeline**: Whisper -> JarvisCore -> `WeatherPlugin` (Open-Meteo REST API) -> Kokoro TTS.

### E. Ask a Web Search Question
- **Voice Input**: *"Jarvis, search the web for latest Python 3.12 features."*
- **Pipeline**: Whisper -> JarvisCore -> `WebSearchPlugin` (DuckDuckGo Search) -> Kokoro TTS.

### F. Ask a Question About an Indexed Document (RAG)
- Place `resume.txt` in `data/documents/` and ask:
- **Voice Input**: *"Jarvis, search my documents for Alex Mercer's skills."*
- **Pipeline**: Whisper -> JarvisCore -> `SearchDocumentsTool` -> `RAGManager` -> `LocalVectorStore` -> Ollama -> Kokoro TTS.

### G. Demonstrate Persistent Memory
- **Voice Input**: *"Jarvis, remember that my favorite color is teal."*
- **Voice Input**: *"Jarvis, what is my favorite color?"*
- **Pipeline**: Whisper -> JarvisCore -> `RememberTool` -> Persistent Memory -> `QueryMemoryTool`.

### H. Demonstrate Mid-Speech Interruption
- While JARVIS is speaking a long response, speak into the microphone or issue a new command.
- **Pipeline**: SpeechManager detects voice during `SPEAKING` -> Transitions to `INTERRUPTED` -> Halts playback -> Flushes queues -> Transitions to `LISTENING`.

---

## 🛠️ Technology Stack

| Category | Component / Library | Description |
| :--- | :--- | :--- |
| **Language & Concurrency** | Python 3.12+, `asyncio` | Asynchronous non-blocking runtime event loop |
| **Local RAG & Embeddings** | `LocalTFIDFEmbeddingProvider`, `LocalVectorStore` | Local document indexing (.txt, .md, .pdf, .docx) |
| **Plugins Infrastructure** | `BasePlugin`, `PluginRegistry`, `PluginManager` | Dynamic loading, permission safety, tool bridging |
| **Web Server & API** | `fastapi`, `uvicorn`, `pydantic`, `httpx` | Local REST API and WebSocket real-time server |
| **CLI & UI** | `typer`, `rich` | Terminal rendering, banners, and structured commands |
| **Speech-to-Text (STT)** | `faster-whisper`, `webrtcvad` | Offline Whisper CTranslate2 engine with WebRTC VAD |
| **Text-to-Speech (TTS)** | `kokoro-onnx`, `soundfile` | High-fidelity local ONNX neural voice generator |
| **LLM Inference** | `ollama`, `httpx` | Local offline Llama 3 / Ollama REST client |
| **Testing** | `pytest`, `pytest-asyncio` | 100% automated test coverage across 17 test modules (88 tests) |

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:
```bash
pytest -v
```
