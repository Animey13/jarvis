# JARVIS: Local AI Assistant Framework

JARVIS is a production-grade, offline-first local AI assistant framework designed for Ubuntu 24.04+ and Python 3.12+. This repository is structured as a portfolio-quality architecture adhering strictly to modern software engineering best practices.

```
      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
      ██║███████║██████╔╝██║   ██║██║███████╗
 ██   ██║██╔══██║██╔══██║╚██╗ ██╔╝██║╚════██║
 ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
```

---

## 🛠️ Architecture & Core Highlights

JARVIS is engineered with a **Clean Architecture** style. High-grade capabilities include:
- **Modular Design & SOLID Principles**: Separation of concerns. Subsystems have strict abstract interfaces (`AudioInput`, `SpeechRecognizer`, `SpeechSynthesizer`), decoupling orchestration logic from implementation.
- **Cascading Configuration System**: Loads configurations from `config/settings.yaml` overridden by environment variables (`.env`).
- **Offline Speech Recognition**: Integrating `faster-whisper` for local Speech-to-Text.
- **Voice Activity Detection (VAD)**: Utilizes `webrtcvad` for continuous silence/speech frame-boundary checks to segment user speech and stop automatically.
- **Wake Word Engine**: Custom wake phrase spotter (defaults to 'Jarvis') with cooling gates and low-confidence trigger suppression.
- **Offline Speech Synthesis**: Employs `piper` neural Text-to-Speech executing fast local wave models and command-line players with response queues and interruption.
- **Microphone Auto-Selection & Resampling**: Automatically detects and picks default recording devices, negotiating supported sample rates and downsampling buffers on the fly to fit Whisper's 16kHz standard.
- **Advanced Logging**: Real-time console visualization via `Rich` matched with rotating files inside `logs/jarvis.log`.

---

## 📂 File Directory Tree & Components

Here is the exact layout of the codebase and the purpose of every file:

```
jarvis/
├── app/
│   ├── __init__.py         # Core package definitions
│   ├── assistant.py        # Central JarvisAssistant controller (lifecycle, event loop, voice loop)
│   └── logging_config.py   # Global logging system (console & file rotating handlers)
├── assets/                 # Graphics, sounds, or other runtime assets
├── config/
│   ├── __init__.py         # Config package definitions
│   ├── config.py           # Configuration parser, dotenv manager, and settings
│   └── settings.yaml       # Global default settings definition
├── docs/
│   └── architecture.md     # Deep-dive system design document
├── llm/
│   ├── __init__.py         # LLM adapters package
│   └── base.py             # Abstract BaseLLMClient interface
├── logs/                   # Target location for system rotating log files
├── memory/
│   ├── __init__.py         # Memory drivers package
│   └── base.py             # Abstract BaseMemory interface
├── plugins/
│   ├── __init__.py         # Extensible plugin package
│   └── base.py             # Abstract BasePlugin interface
├── speech/
│   ├── __init__.py         # Unified Speech package exports
│   ├── base.py             # Abstract STT & TTS interfaces (Phase 1 legacy support)
│   ├── interfaces.py       # Production abstract base classes (AudioInput, STT, TTS)
│   ├── manager.py          # Central SpeechManager coordinator (state loops)
│   ├── microphone.py       # Hardware mic manager, default rate negotiator & resampler
│   ├── recognizer.py       # Whisper and WebRTC VAD voice-recording boundaries
│   ├── synthesizer.py      # Piper TTS synthesis background consumer & playbacks
│   └── wakeword.py         # WakeWord phrase spotter and gating checks
├── tests/
│   ├── __init__.py         # Testing package
│   ├── test_assistant.py   # Unit tests for assistant execution & loop signals
│   ├── test_config.py      # Unit tests for configuration settings & overrides
│   ├── test_logging.py     # Unit tests for log writing and formatting
│   └── test_speech.py      # Unit tests for mic stream, VAD, Whisper, wake word, and manager
├── tools/
│   ├── __init__.py         # Agent tools package
│   └── base.py             # Abstract BaseTool interface
├── ui/
│   ├── __init__.py         # Core UI rendering package
│   └── base.py             # Abstract BaseUserInterface interface
├── .env                    # System-specific environment overrides (git-ignored)
├── .env.example            # Environment variables template
├── .gitignore              # Files to ignore in git commits
├── demo_speech.py          # Independent demonstration script of the Speech Layer
├── main.py                 # Core CLI entrypoint
├── requirements.txt        # Production, speech, and development dependencies
└── setup_env.sh            # Helper script to bootstrap environment settings
```

---

## 🚀 Setup & Execution Instructions

Follow these steps to set up and run JARVIS on an Ubuntu-compatible environment:

### 1. Environment Setup

Configure environment files and variables:
```bash
# Copy settings template
cp .env.example .env
```

### 2. Dependency Installation

Install all core dependencies:
```bash
pip install -r requirements.txt
```

### 3. Running JARVIS Commands

JARVIS exposes commands through `main.py` using `typer`:

#### View System Version
```bash
python main.py version
```

#### View Active System Configurations
Prints a beautifully-formatted hierarchical tree representing the loaded config values, merging default files with your `.env` overrides:
```bash
python main.py config
```

#### Start Assistant with Voice Interaction Loop
Launches JARVIS, prints the microphone setup configurations, opens the physical audio stream, and waits for your voice:
```bash
python main.py start
```
*   **Voice Test Loop**: Speak [bold yellow]'Jarvis'[/bold yellow]. The console will notify `Listening...`. Speak your command (e.g. `Hello`). JARVIS will transcribe and speak back to you directly: `You said Hello`.
*   **Console Override**: Type `exit` or `quit` to cleanly exit the assistant.

---

## 🧪 Testing System

JARVIS uses `pytest` for highly modular, fully-typed test coverage. All async tests utilize `pytest-asyncio`.

Run the automated test suite:
```bash
pytest -v
```

---

## 💡 Key Architectural Design Decisions

1. **Auto-Device Selection & Resampling**: MicrophoneManager queries sounddevice and auto-selects default hardware inputs. If the hardware samplerate differs from 16kHz, linear interpolation resamples the PCM frame arrays in real-time, matching Whisper and WebRTC VAD expectations.
2. **Deterministic Simulation Gating**: Simulator mode is disabled in production. It is activated automatically ONLY if no physical input hardware exists, if Sounddevice/PortAudio fails to load, or if explicitly enabled inside unit tests and the standalone demo.
3. **Interruptible TTS Playback**: When new spoken responses are requested, current CLI player processes (`aplay`/`paplay`/`ffplay`) are instantly terminated, yielding zero-latency conversational cuts.
