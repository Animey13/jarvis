# JARVIS: Local AI Assistant Framework (Phase 1)

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

## 🛠️ Phase 1 Architecture & Highlights

This phase establishes the foundational architecture of the JARVIS platform. Key capabilities implemented:
- **Modular Design & SOLID Principles**: Absolute separation of concerns. All subsystems have strict interfaces, decoupling execution logic from specific implementations.
- **Robust Configuration System**: Loads cascading configurations from `config/settings.yaml` overridden by environment variables (`.env`) using `pathlib` and `python-dotenv`.
- **Advanced Logging Infrastructure**: Unified logger with `Rich` colored/traceback terminal formatting and `RotatingFileHandler` writing structured logs to `logs/jarvis.log`.
- **Asynchronous Loop Controller**: Structured command CLI engine utilizing `asyncio` with proper signal handling for graceful shutdown on Ubuntu (SIGINT, SIGTERM).
- **Graceful Error Management**: Standardized global exception hooks and elegant recovery paths.
- **CLI Commands with Typer**: User commands map cleanly to system targets (e.g. `start`, `config`, `version`).

---

## 📂 File Directory Tree & Components

Here is the exact layout of the codebase and the purpose of every file:

```
jarvis/
├── app/
│   ├── __init__.py         # Core package definitions
│   ├── assistant.py        # Central JarvisAssistant controller (lifecycle, event loop)
│   └── logging_config.py   # Global logging system (console & file handler setup)
├── assets/                 # Graphics, sounds, or other runtime assets
├── config/
│   ├── __init__.py         # Config package definitions
│   ├── config.py           # Configuration parser, dotenv manager, and Settings singleton
│   └── settings.yaml       # Global default settings definition
├── docs/
│   └── architecture.md     # Deep-dive system design document
├── llm/
│   ├── __init__.py         # LLM adapters package
│   └── base.py             # Abstract BaseLLMClient interface
├── logs/                   # Target location for system log files
├── memory/
│   ├── __init__.py         # Memory drivers package
│   └── base.py             # Abstract BaseMemory interface
├── plugins/
│   ├── __init__.py         # Extensible plugin package
│   └── base.py             # Abstract BasePlugin interface
├── speech/
│   ├── __init__.py         # Speech adapters package
│   └── base.py             # Abstract STT & TTS interfaces
├── tests/
│   ├── __init__.py         # Testing package
│   ├── test_assistant.py   # Unit tests for core execution loop & signals
│   ├── test_config.py      # Unit tests for configuration settings & overrides
│   └── test_logging.py     # Unit tests for log writing and formatting handlers
├── tools/
│   ├── __init__.py         # Agent tools package
│   └── base.py             # Abstract BaseTool interface
├── ui/
│   ├── __init__.py         # Core UI rendering package
│   └── base.py             # Abstract BaseUserInterface interface
├── .env                    # System-specific environment overrides (git-ignored)
├── .env.example            # Environment variables template
├── .gitignore              # Files to ignore in git commits
├── main.py                 # Core CLI entrypoint
├── requirements.txt        # Production & development dependencies
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

JARVIS exposes various commands through `main.py` using `typer`:

#### View System Version
```bash
python main.py version
```

#### View Active System Configurations
Prints a beautifully-formatted hierarchical tree representing the loaded config values, merging default files with your `.env` overrides:
```bash
python main.py config
```

#### Start Interactive Assistant CLI
Launches JARVIS, shows the stylish ASCII banner, initializes the asynchronous runtime, and opens the prompt:
```bash
python main.py start
```
*At the prompt, type your message or commands. Enter `exit` or `quit` to cleanly exit.*

---

## 🧪 Testing System

JARVIS uses `pytest` for highly modular, fully-typed test coverage. All async tests utilize `pytest-asyncio`.

Run the automated test suite:
```bash
pytest -v
```

---

## 💡 Key Architectural Design Decisions

1. **Strict Python Type Hints**: Every variable, parameter, and function signature is fully typed.
2. **Interface Isolation**: The foundation dictates *how* future systems communicate via Abstract Base Classes. There are absolutely no "placeholders" or `TODO` annotations, only real abstract contracts.
3. **Responsive Async Shell Loop**: To prevent standard terminal `input()` from locking the `asyncio` event loop (blocking other coroutines or signal captures), input prompt reads are routed to standard execution threads using `loop.run_in_executor(None, ...)`.
4. **Clean Logging Formats**: Beautiful, colored visual logs on the terminal (with detailed traceback inspection) paired with structured, standard timestamp-stamped rotation logs inside `logs/jarvis.log`.
