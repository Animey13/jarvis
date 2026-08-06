# JARVIS: Architectural Design & Patterns

This document details the architectural decisions and patterns selected for the core foundation of **JARVIS** (Local AI Assistant).

---

## 1. High-Level Architectural Patterns

JARVIS adopts **Clean Architecture** combined with **Domain-Driven Design (DDD)** concepts. This isolates the core orchestration layer from volatile infrastructure details (like specific LLM models, TTS voice libraries, or UI frontends).

### Interface Segregation & Dependency Inversion
All external system integrations (Language Models, Speech Synthesis, Memory Stores, UI displays) are defined as strict abstract interfaces (`ABC` / Protocols) under their respective directories:
- `llm/base.py` -> `BaseLLMClient`
- `speech/base.py` -> `BaseSpeechToText` & `BaseTextToSpeech`
- `tools/base.py` -> `BaseTool`
- `memory/base.py` -> `BaseMemory`
- `ui/base.py` -> `BaseUserInterface`
- `plugins/base.py` -> `BasePlugin`

The core application orchestration (e.g. `JarvisAssistant` in `app/assistant.py`) interacts purely with these abstractions rather than concrete modules. In Phase 2, concrete classes (such as `OllamaLLMClient` or `WhisperSTT`) will be injected, keeping the assistant decoupled and easily testable.

---

## 2. Solid Principles Applied

### Single Responsibility Principle (SRP)
- `config/config.py` is solely responsible for loading settings from files/environments and resolving values.
- `app/logging_config.py` is solely responsible for setting up console formatters and rotating files.
- `app/assistant.py` governs the central execution loop.
- `main.py` is dedicated to CLI command mapping.

### Open/Closed Principle (OCP)
The registration systems for tools, memories, and plugins are open to extension (you can add new tools or plugins by simply implementing the base abstract class and registering them) but closed for modification of core orchestration logic.

### Liskov Substitution Principle (LSP)
Any concrete implementation of `BaseLLMClient` or `BaseTool` will be fully substitutable for its abstract interface without altering assistant behaviors or throwing unexpected signatures.

---

## 3. Concurrency & Event Loop Model

JARVIS is built for highly responsive terminal interactions and real-time audio streams. It employs **asyncio** as the core runtime.
- Blocking functions (such as reading terminal inputs or interacting with slow OS channels) are executed inside separate thread-pool executors (`loop.run_in_executor(None, ...)`). This ensures the async event loop remains unblocked, responding to OS signals, stream processing, or background notifications.

---

## 4. Environment & Platform Constraints
- **Ubuntu 24.04+ Compatibility**: Leverages standard POSIX signals (`SIGINT` and `SIGTERM`) directly on the event loop for graceful teardown.
- **Offline First**: All configurations are structured to prioritize local resources (e.g. localhost API endpoints, local directories).
