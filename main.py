"""
JARVIS Core CLI Entrypoint.

This is the main entry point for running the JARVIS assistant. It utilizes Typer
to provide an elegant command-line interface for starting the assistant,
viewing configurations, and checking the system version.
"""

import asyncio
import logging
import sys
import typer

from app.assistant import JarvisAssistant
from app.logging_config import configure_logging
from config.config import settings

# Initialize Typer App
app = typer.Typer(
    name="jarvis",
    help="JARVIS: A production-grade local AI assistant.",
    add_completion=False
)

logger = logging.getLogger(__name__)


@app.command(name="start")
def start() -> None:
    """
    Start the JARVIS assistant interactive shell.
    """
    # 1. Initialize logging
    configure_logging(
        log_level=settings.logging.level,
        log_file=settings.get_log_file_path(),
        console_output=settings.logging.console_output
    )

    logger.info("Initializing JARVIS CLI interface...")

    # 2. Instantiate and start Assistant
    assistant = JarvisAssistant(settings=settings)
    try:
        asyncio.run(assistant.start())
    except KeyboardInterrupt:
        logger.warning("Assistant process interrupted by user.")
        print("\n[bold red]JARVIS: Execution interrupted. Exiting.[/bold red]")
        sys.exit(0)
    except Exception as e:
        logger.critical("Failed to start JARVIS: %s", e, exc_info=True)
        print(f"CRITICAL ERROR: Failed to run JARVIS assistant: {e}")
        sys.exit(1)


@app.command(name="config")
def config() -> None:
    """
    Display the active configuration settings in a structured layout.
    """
    from rich.console import Console
    from rich.tree import Tree

    console = Console()
    tree = Tree("[bold cyan]JARVIS System Configurations[/bold cyan]")

    app_branch = tree.add("[bold green]Application[/bold green]")
    app_branch.add(f"Name: [yellow]{settings.app.name}[/yellow]")
    app_branch.add(f"Environment: [yellow]{settings.app.env}[/yellow]")
    app_branch.add(f"Debug Mode: [yellow]{settings.app.debug}[/yellow]")

    logging_branch = tree.add("[bold green]Logging[/bold green]")
    logging_branch.add(f"Level: [yellow]{settings.logging.level}[/yellow]")
    logging_branch.add(f"File Path: [yellow]{settings.logging.file_path}[/yellow]")
    logging_branch.add(f"Console Output: [yellow]{settings.logging.console_output}[/yellow]")

    llm_branch = tree.add("[bold green]Language Model (LLM)[/bold green]")
    llm_branch.add(f"Provider: [yellow]{settings.llm.provider}[/yellow]")
    llm_branch.add(f"Model: [yellow]{settings.llm.model}[/yellow]")
    llm_branch.add(f"API Base: [yellow]{settings.llm.api_base}[/yellow]")
    llm_branch.add(f"Timeout: [yellow]{settings.llm.timeout}s[/yellow]")

    speech_branch = tree.add("[bold green]Speech & Voice[/bold green]")
    speech_branch.add(f"Input Device: [yellow]{settings.speech.input_device}[/yellow]")
    speech_branch.add(f"TTS Provider: [yellow]{settings.speech.tts_provider}[/yellow]")
    speech_branch.add(f"Voice ID: [yellow]{settings.speech.voice_id}[/yellow]")

    console.print(tree)


@app.command(name="version")
def version() -> None:
    """
    Display version and release information for JARVIS.
    """
    from rich.console import Console
    console = Console()
    console.print("[bold cyan]JARVIS Local AI Assistant[/bold cyan]")
    console.print("Version: [bold green]0.1.0-alpha[/bold green]")
    console.print("Compatibility: [yellow]Ubuntu 24.04+ & Python 3.12+[/yellow]")
    console.print("[dim]A production-grade, offline-first local AI companion platform.[/dim]")


if __name__ == "__main__":
    app()
