"""
JARVIS Core Assistant Module.

This module defines the main JarvisAssistant class which manages the application
lifecycle, handles graceful shutdown, and executes the interactive CLI shell loop.
"""

import asyncio
import logging
import signal
from typing import Optional

from rich.console import Console
from rich.prompt import Prompt

from config.config import Settings

logger = logging.getLogger(__name__)


class JarvisAssistant:
    """
    Core Jarvis Assistant controller that coordinates subsystems and handles the execution loop.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initializes the assistant with the provided settings.

        Args:
            settings: Loaded configuration settings.
        """
        self.settings: Settings = settings
        self.console: Console = Console()
        self.is_running: bool = False
        self._shutdown_event: Optional[asyncio.Event] = None

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
        self.console.print(" Type [bold red]exit[/bold red] or [bold red]quit[/bold red] to stop the assistant.")
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
                # Fallback for environments where loop.add_signal_handler is not supported
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
                # Wrap input in run_in_executor to keep the async loop active for timers and signal handlers
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

                logger.debug("Received input: %s", user_input)
                self.console.print(f"[bold blue]JARVIS Foundation Response:[/bold blue] Base is ready! Command received: [italic]'{user_input}'[/italic]. (AI Features will be integrated in Phase 2.)")

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

        # In future phases: Close databases, disconnect voice channels, save state here.
        await asyncio.sleep(0.1) # Simulate teardown overhead

        self.console.print("[bold cyan]JARVIS: Offline. Goodbye.[/bold cyan]")
        logger.info("JARVIS stopped successfully.")
