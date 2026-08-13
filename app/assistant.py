"""
JARVIS Core Assistant Module.

Coordinates the main application lifecycle and integrates the SpeechManager
to implement a local offline speech interaction loop (Voice Test).
"""

import asyncio
import json
import logging
import signal
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from config.config import Settings
from speech.manager import SpeechManager
from llm.ollama import OllamaClient
from memory.local_json import LocalJSONMemory
from tools.registry import ToolRegistry
from tools.system_tools import DateTimeTool, SystemStatusTool

logger = logging.getLogger(__name__)


class JarvisAssistant:
    """
    Core Jarvis Assistant controller that coordinates subsystems and handles the execution loop.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initializes the assistant with the provided settings and speech manager.

        Args:
            settings: Loaded configuration settings.
        """
        self.settings: Settings = settings
        self.console: Console = Console()
        self.is_running: bool = False
        self._shutdown_event: Optional[asyncio.Event] = None

        # Initialize local LLM Client
        logger.info("Initializing local LLM client...")
        self.llm_client: OllamaClient = OllamaClient(
            model_name=settings.llm.model,
            api_base=settings.llm.api_base,
            timeout=settings.llm.timeout
        )

        # Initialize local episodic JSON memory
        logger.info("Initializing local memory driver...")
        self.memory: LocalJSONMemory = LocalJSONMemory()

        # Initialize Tool Registry
        logger.info("Initializing local tool registry...")
        self.tool_registry: ToolRegistry = ToolRegistry()
        self.tool_registry.register_tool(DateTimeTool())
        self.tool_registry.register_tool(SystemStatusTool())

        # Initialize the Speech Manager
        logger.info("Initializing Jarvis Core Speech subsystem...")
        self.speech_manager: SpeechManager = SpeechManager(settings=settings)

        # Register conversational Speech responder callback: Speech -> LLM -> TTS
        async def voice_test_callback(prompt: str) -> str:
            self.console.print(f"\n[bold green]🎙️  [Voice Interaction] Transcribed:[/bold green] [italic yellow]'{prompt}'[/italic yellow]")
            response = await self.process_text_input(prompt)
            self.console.print(f"[bold blue]🎙️  [Voice Interaction] Assistant response:[/bold blue] [italic white]\"{response}\"[/italic white]\n")
            return response

        self.speech_manager.register_speech_callback(voice_test_callback)

    async def process_text_input(self, prompt: str) -> str:
        """
        Processes a user text prompt through memory retrieval, tool parsing/execution,
        and LLM response generation.

        Args:
            prompt: User text query.

        Returns:
            str: Assistant response.
        """
        # 1. Retrieve conversation context
        try:
            history_turns = await self.memory.retrieve("", limit=4)
            context_str = ""
            if history_turns:
                context_str = "Recent conversation context:\n"
                for turn in history_turns:
                    role = turn.get("metadata", {}).get("role", "user").upper()
                    content = turn.get("content", "")
                    context_str += f"{role}: {content}\n"
                context_str += "\n"
        except Exception as e:
            logger.error("Failed to retrieve conversation history: %s", e)
            context_str = ""

        # 2. Build full prompt and tools description
        full_prompt = f"{context_str}Current User Prompt: {prompt}"
        tools_description = self.tool_registry.get_tools_prompt_description()
        system_prompt = (
            "You are JARVIS, a helpful, polite, and extremely concise local AI assistant. "
            "Keep responses under 2-3 short sentences.\n\n"
            f"{tools_description}"
        )

        # 3. First LLM query
        try:
            response = await self.llm_client.generate(full_prompt, system_prompt=system_prompt)
        except Exception as e:
            logger.warning("Local LLM primary query failed: %s. Falling back to simple answer.", e)
            return f"I am currently disconnected from my local language model, but I heard you say: {prompt}"

        # 4. Check for tool invocation
        tool_call = self.tool_registry.parse_tool_call(response)
        if tool_call:
            tool_name, tool_args = tool_call
            self.console.print(f"[dim][*] Tool call detected: {tool_name}({tool_args}). Executing...[/dim]")

            # Execute tool
            tool_result = await self.tool_registry.execute_tool(tool_name, **tool_args)
            self.console.print(f"[dim][*] Tool execution completed. Result: {tool_result}[/dim]")

            # Construct follow-up turn
            follow_up_prompt = (
                f"{context_str}"
                f"User original query: {prompt}\n\n"
                f"Real-time system tool execution result for '{tool_name}':\n"
                f"{json.dumps(tool_result, indent=2) if isinstance(tool_result, dict) else str(tool_result)}\n\n"
                "Please construct a friendly, conversational final response incorporating this live system data. "
                "Keep the reply precise, natural, and under 2-3 short sentences."
            )

            follow_up_system = (
                "You are JARVIS, a helpful, polite, and extremely concise local AI assistant. "
                "Always use the provided real-time system tool execution data to accurately answer the user's query."
            )

            # Second LLM query to synthesize tool output
            try:
                response = await self.llm_client.generate(follow_up_prompt, system_prompt=follow_up_system)
            except Exception as e:
                logger.warning("Local LLM tool synthesis query failed: %s. Using raw tool response.", e)
                response = f"I executed {tool_name} and received the following status: {tool_result}"

        # 5. Store the successful conversation turn in memory
        try:
            await self.memory.store(prompt, {"role": "user"})
            await self.memory.store(response, {"role": "assistant"})
        except Exception as e:
            logger.error("Failed to store conversation turn in memory: %s", e)

        return response

    def display_banner(self) -> None:
        """Displays a beautiful, production-grade ASCII banner for JARVIS."""
        banner_text = """
[bold cyan]      ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗[/bold cyan]
[bold cyan]      ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝[/bold cyan]
[bold cyan]      ██║███████║██████╔╝██║   ██║██║███████╗[/bold cyan]
[bold blue] ██   ██║██╔══██║██╔══██║╚██╗ ██╔╝██║╚════██║[/bold blue]
[bold blue] ╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║[/bold blue]
[bold blue]  ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝[/bold blue]
"""
        self.console.print(banner_text)
        self.console.print(f"[bold green] Jarvis Assistant (v0.1.0) [/bold green] - [italic yellow]Platform: Ubuntu-Compatible[/italic yellow]")
        self.console.print(f" Environment: [bold magenta]{self.settings.app.env}[/bold magenta] | Debug: [bold]{self.settings.app.debug}[/bold]")
        self.console.print("[dim]-------------------------------------------------------------[/dim]")
        self.console.print(" Voice Activation: Speak [bold yellow]'Jarvis'[/bold yellow] followed by your command.")
        self.console.print(" Console Interface: Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to stop.")
        self.console.print("[dim]-------------------------------------------------------------[/dim]\n")

    def _setup_signal_handlers(self) -> None:
        """Registers OS signal handlers (SIGINT, SIGTERM) for Ubuntu-compatible graceful shutdown."""
        loop = asyncio.get_running_loop()

        def signal_handler(sig: int) -> None:
            logger.warning("Received OS signal %s. Initiating graceful shutdown...", sig)
            self.console.print(f"\n[bold red][!] Signal received ({signal.Signals(sig).name}). Shutting down gracefully...[/bold red]")
            if self._shutdown_event:
                self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
            except NotImplementedError:
                pass

    async def start(self) -> None:
        """
        Starts the JARVIS assistant, initializes systems, and enters the runtime execution.
        """
        if self.is_running:
            logger.warning("JARVIS is already running.")
            return

        logger.info("Starting JARVIS Core Subsystems...")
        self.is_running = True
        self._shutdown_event = asyncio.Event()

        # Display UI Banner
        self.display_banner()

        # Setup OS Signal handlers
        self._setup_signal_handlers()

        # Start the background Speech Manager orchestration
        try:
            await self.speech_manager.start()
        except Exception as e:
            logger.error("Failed to start SpeechManager stream: %s. Continuing with terminal-only.", e)
            self.console.print(f"[bold yellow]Warning: Speech Layer failed to start ({e}). Running in terminal-only mode.[/bold yellow]")

        # Execute main loop
        try:
            await self._run_loop()
        except asyncio.CancelledError:
            logger.info("Main execution task cancelled.")
        except Exception as e:
            logger.exception("Unexpected exception occurred in assistant main execution loop: %s", e)
            self.console.print(f"[bold red]CRITICAL: Subsystem error: {e}[/bold red]")
        finally:
            await self.stop()

    async def _run_loop(self) -> None:
        """Runs the primary console interaction loop as an asynchronous task."""
        assert self._shutdown_event is not None
        loop = asyncio.get_running_loop()

        while not self._shutdown_event.is_set():
            try:
                user_input = await loop.run_in_executor(
                    None,
                    lambda: Prompt.ask("[bold green]jarvis>[/bold green]")
                )

                clean_input = user_input.strip().lower()
                if clean_input in ("exit", "quit", "q"):
                    logger.info("User requested shutdown.")
                    self._shutdown_event.set()
                    break

                if not clean_input:
                    continue

                logger.debug("Received console input: %s", user_input)
                self.console.print("[dim][*] Processing query...[/dim]")
                response = await self.process_text_input(user_input)
                self.console.print(f"[bold blue]JARVIS Response:[/bold blue] {response}")

            except (KeyboardInterrupt, EOFError):
                logger.info("Console interrupted (EOF/KeyboardInterrupt).")
                self._shutdown_event.set()
                break
            except Exception as e:
                logger.exception("Error processing user input: %s", e)
                self.console.print(f"[bold red]Error: {e}[/bold red]")

    async def stop(self) -> None:
        """
        Stops the JARVIS assistant and cleans up resources gracefully.
        """
        if not self.is_running:
            return

        logger.info("Stopping JARVIS and cleaning up resources...")
        self.is_running = False

        # Stop Speech Manager
        try:
            await self.speech_manager.stop()
        except Exception as e:
            logger.error("Error stopping SpeechManager: %s", e)

        await asyncio.sleep(0.1) # Simulate teardown overhead

        self.console.print("[bold cyan]JARVIS: Offline. Goodbye.[/bold cyan]")
        logger.info("JARVIS stopped successfully.")
