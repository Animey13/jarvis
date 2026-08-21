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

## ✨ Features

- **Local Vector Embeddings & RAG**: Fully local, offline Retrieval-Augmented Generation (`rag/`) allowing JARVIS to ingest, index, search, and answer questions from local documents (`.txt`, `.md`, `.pdf`, `.docx`) using local TF-IDF vector embeddings, disk-backed vector store (`data/rag/vector_store.json`), and citation formatting.
- **Custom Plugin Architecture & API Integrations**: Modular plugin infrastructure (`BasePlugin`, `PluginRegistry`, `PluginManager`) with explicit permission levels (`READ_ONLY`, `NETWORK`, `FILESYSTEM`, `SYSTEM`, `EXECUTION`), failure isolation, tool bridging, and graceful offline degradation.
- **Built-in Plugins**: Includes `SystemPlugin` (diagnostics, datetime, file operations, math), `WeatherPlugin` (location forecasts via Open-Meteo with offline fallbacks), and `WebSearchPlugin` (provider-agnostic search engine via DuckDuckGo with offline fallbacks).
- **Interactive Local Web Dashboard (FastAPI + WebSockets)**: Real-time graphical user interface displaying voice interaction state, scrolling live event feeds, conversation log, local documents panel, plugins management, registered tools, persistent memory management, and system diagnostics.
- **Continuous Voice Interaction State Machine**: Formal state loop (`WAKING`, `LISTENING`, `TRANSCRIBING`, `THINKING`, `SPEAKING`, `INTERRUPTED`, `ERROR`, `SHUTDOWN`) with transition logging and deterministic state flow.
- **Mid-Speech Voice Interruption**: Speak at any time while JARVIS is responding; playback immediately halts, audio queues flush, and your new command is captured.
- **Hardware-Resilient Microphone Capture**: Auto-configures PortAudio/sounddevice to target system default ALSA inputs using native `float32` capture, automatically handling sample rate downsampling and clipping guards to deliver pristine 16 kHz mono PCM bytes to Whisper.
- **Local Neural Speech Synthesis (Kokoro ONNX)**: Ultra-realistic local voice generation (default `af_sky` voice) executing ONNX models with zero cloud latency.
- **Local Asynchronous LLM Orchestration**: Non-blocking `OllamaClient` communicating over local HTTP REST endpoints, featuring fail-safe spoken fallbacks.
- **Dual Memory Subsystem**: Bounded short-term in-session conversation history paired with persistent, disk-backed JSON fact storage (`logs/persistent_memory.json`) featuring auto-recovery from corrupted files.

---

## 📚 RAG Subsystem & Document Ingestion Guide

### Document Ingestion & Querying
Ingest local documents (`.txt`, `.md`, `.pdf`, `.docx`) into `data/documents/`:
```bash
# Upload document via Web Dashboard or copy file to data/documents/
cp resume.pdf data/documents/
```

Ask voice queries like:
- *"Jarvis, what does my resume say about machine learning?"*
- *"Search my documents for internship experience."*
- *"What does the project report say about the architecture?"*

JARVIS routes the request through `SearchDocumentsTool` -> `RAGManager` -> `LocalVectorStore` -> `OllamaClient` -> `KokoroSynthesizer` naturally.

---

## 🖥️ Web Dashboard Launch & Usage

Launch the local Web Dashboard server:
```bash
# Launch Dashboard (REST & WebSockets on http://127.0.0.1:8000)
python main.py dashboard

# Launch Dashboard alongside background voice assistant loop
python main.py dashboard --with-assistant
```

Navigate to: `http://127.0.0.1:8000`

---

## 🧪 Running Automated Tests

Run the complete test suite using `pytest`:
```bash
pytest -v
```
