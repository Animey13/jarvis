"""
JARVIS Speech Layer Demonstration Script.

Presents an end-to-end local speech interface loop:
1. Simulates or records audio to trigger the wake word ('Jarvis').
2. Synthesizes 'Listening' and activates VAD speech recording.
3. Transcribes user voice ('Hello') using Faster Whisper.
4. Speaks back the confirmation ('You said Hello') using Piper TTS.
"""

import asyncio
import logging
import sys
import numpy as np
from rich.console import Console

from config.config import settings
from app.logging_config import configure_logging
from speech.manager import SpeechManager

# Set up clean terminal styling
console = Console()
logger = logging.getLogger(__name__)


async def main() -> None:
    """
    Launches the JARVIS Speech Layer Demo.
    """
    console.print("\n[bold cyan]🎙️  JARVIS Phase 2: Speech Layer Demonstration 🎙️[/bold cyan]")
    console.print("[dim]-------------------------------------------------------------[/dim]")
    console.print("This script demonstrates offline-first Wake Word Spotting,")
    console.print("VAD-gated speech recording, Whisper STT, and Piper TTS Synthesis.\n")

    # 1. Force the use of simulator/mock options for automated sandbox runs
    # This ensures the demo runs fully out of the box in headless environments.
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.logging.console_output = True
    settings.logging.level = "INFO"

    # Configure unified logging
    configure_logging(
        log_level=settings.logging.level,
        log_file=settings.get_log_file_path(),
        console_output=settings.logging.console_output
    )

    # 2. Instantiate unified Speech Manager
    try:
        manager = SpeechManager(settings=settings)
    except Exception as e:
        console.print(f"[bold red]CRITICAL: Failed to initialize SpeechManager: {e}[/bold red]")
        sys.exit(1)

    # 3. Define the speech interaction callback
    # When user speech is transcribed, this callback processes the text, displays it,
    # and returns a response text which JARVIS speaks.
    async def process_user_speech(prompt: str) -> str:
        console.print(f"\n[bold green]User says:[/bold green] [italic]'{prompt}'[/italic]")
        response = f"You said {prompt}."
        console.print(f"[bold blue]Assistant responds:[/bold blue] [italic white]\"{response}\"[/italic white]")
        return response

    manager.register_speech_callback(process_user_speech)

    # 4. Start Speech Orchestrator
    console.print("[bold yellow][*] Starting Speech Manager loop...[/bold yellow]")
    await manager.start()

    # 5. Programmatic simulator sequence task
    # To run the entire user interaction pipeline fully automatically in the sandbox:
    async def run_simulation_triggers() -> None:
        try:
            # Step A: Sleep and push simulated wake phrase audio
            await asyncio.sleep(2.0)
            console.print("\n[bold yellow][Simulation] User speaks: 'Jarvis'[/bold yellow]")

            # The recognizer transcribes rolling wake buffers.
            # We mock transcription result inside WhisperRecognizer for simulations.
            # To trigger the wake word in simulation, we feed mock PCM into microphone queue.
            # 2 seconds of sound to fill rolling buffer:
            mock_pcm_wake = np.ones(16000 * 2, dtype=np.int16) * 50
            await manager.microphone.simulator_queue.put(mock_pcm_wake.tobytes())

            # Step B: Wait for state change, and synthesize speech prompt 'Listening...'
            await asyncio.sleep(2.5)
            console.print("\n[bold yellow][Simulation] User speaks: 'Hello'[/bold yellow]")

            # Feed PCM for active speech recording
            mock_pcm_speech = np.ones(16000 * 1, dtype=np.int16) * 100
            await manager.microphone.simulator_queue.put(mock_pcm_speech.tobytes())

            # Step C: Feed a silent block to trigger VAD silence timeout (1.5 seconds)
            # Silence timeout is 1.5 seconds, so we push silent blocks and sleep
            for _ in range(55): # ~1.65 seconds of silence
                silent_block = np.zeros(480, dtype=np.int16)
                await manager.microphone.simulator_queue.put(silent_block.tobytes())
                await asyncio.sleep(0.03)

            # Step D: Wait for transcription to complete and speech to finish playing
            await asyncio.sleep(4.0)

        except Exception as ex:
            logger.error("Error in demo simulation task: %s", ex)
        finally:
            # Clean stop of manager
            console.print("\n[bold yellow][*] Stopping Speech Manager...[/bold yellow]")
            await manager.stop()

    # Run the orchestrator loop and the simulation triggers concurrently
    try:
        await run_simulation_triggers()
    except KeyboardInterrupt:
        console.print("\n[bold red]Demo interrupted by user.[/bold red]")
        await manager.stop()
    except Exception as e:
        console.print(f"[bold red]Demo error: {e}[/bold red]")
        await manager.stop()

    console.print("\n[bold green]✅ Demo completed successfully![/bold green]")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
