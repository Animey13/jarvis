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

    mic_branch = tree.add("[bold green]Microphone[/bold green]")
    mic_branch.add(f"Device: [yellow]{settings.microphone.device}[/yellow]")
    mic_branch.add(f"Sample Rate: [yellow]{settings.microphone.sample_rate}Hz[/yellow]")
    mic_branch.add(f"Channels: [yellow]{settings.microphone.channels}[/yellow]")
    mic_branch.add(f"Use Simulator: [yellow]{settings.microphone.use_simulator}[/yellow]")

    vad_branch = tree.add("[bold green]Voice Activity Detection (VAD)[/bold green]")
    vad_branch.add(f"Sensitivity: [yellow]{settings.vad.sensitivity}[/yellow]")
    vad_branch.add(f"Silence Timeout: [yellow]{settings.vad.silence_timeout}s[/yellow]")
    vad_branch.add(f"Min Speech Duration: [yellow]{settings.vad.min_speech_duration}s[/yellow]")

    whisper_branch = tree.add("[bold green]Speech-to-Text (Whisper)[/bold green]")
    whisper_branch.add(f"Model: [yellow]{settings.whisper.model}[/yellow]")
    whisper_branch.add(f"Language: [yellow]{settings.whisper.language}[/yellow]")
    whisper_branch.add(f"Compute Type: [yellow]{settings.whisper.compute_type}[/yellow]")
    whisper_branch.add(f"Use GPU: [yellow]{settings.whisper.use_gpu}[/yellow]")

    wakeword_branch = tree.add("[bold green]Wake Word[/bold green]")
    wakeword_branch.add(f"Phrase: [yellow]{settings.wakeword.phrase}[/yellow]")
    wakeword_branch.add(f"Cooldown: [yellow]{settings.wakeword.cooldown}s[/yellow]")
    wakeword_branch.add(f"Accidental Prob Limit: [yellow]{settings.wakeword.ignore_accidental_probability}[/yellow]")

    piper_branch = tree.add("[bold green]Text-to-Speech (Piper)[/bold green]")
    piper_branch.add(f"Voice: [yellow]{settings.piper.voice}[/yellow]")
    piper_branch.add(f"Speed Rate: [yellow]{settings.piper.speed}x[/yellow]")
    piper_branch.add(f"Piper Path: [yellow]{settings.piper.piper_path}[/yellow]")
    piper_branch.add(f"Use Simulator: [yellow]{settings.piper.use_simulator}[/yellow]")

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


@app.command(name="test-tts")
def test_tts() -> None:
    """
    Speaks a test sentence using Piper offline TTS.
    Does not require a microphone.
    """
    configure_logging(
        log_level=settings.logging.level,
        log_file=settings.get_log_file_path(),
        console_output=settings.logging.console_output
    )

    print("[*] Initializing Piper TTS...")
    from speech.synthesizer import PiperSynthesizer
    synthesizer = PiperSynthesizer(
        voice=settings.piper.voice,
        speed=settings.piper.speed,
        piper_path=settings.piper.piper_path,
        use_simulator=settings.piper.use_simulator
    )

    test_phrase = "Hello. This is JARVIS speaking."
    print(f"[*] Speaking: '{test_phrase}'")

    try:
        asyncio.run(synthesizer.speak(test_phrase))
        print("[+] TTS test complete.")
    except Exception as e:
        print(f"[-] TTS test failed: {e}")
        sys.exit(1)


@app.command(name="test-mic")
def test_mic() -> None:
    """
    Records 5 seconds of audio from the microphone and transcribes it using Faster Whisper.
    """
    configure_logging(
        log_level=settings.logging.level,
        log_file=settings.get_log_file_path(),
        console_output=settings.logging.console_output
    )

    print("[*] Initializing Microphone and Speech Recognizer...")
    from speech.microphone import MicrophoneManager
    from speech.recognizer import FasterWhisperRecognizer

    microphone = MicrophoneManager(
        device=settings.microphone.device,
        sample_rate=settings.microphone.sample_rate,
        channels=settings.microphone.channels,
        use_simulator=settings.microphone.use_simulator
    )

    recognizer = FasterWhisperRecognizer(
        model_name=settings.whisper.model,
        language=settings.whisper.language,
        compute_type=settings.whisper.compute_type,
        use_gpu=settings.whisper.use_gpu,
        vad_sensitivity=settings.vad.sensitivity,
        silence_timeout=settings.vad.silence_timeout,
        min_speech_duration=settings.vad.min_speech_duration,
        device_name=settings.microphone.device
    )

    async def record_and_transcribe():
        print("[*] Starting audio stream...")
        microphone.start_stream()
        print("[*] Recording 5 seconds... Speak now!")

        audio_buffer = []
        # 5 seconds is 5 / 0.03 = ~167 chunks
        for i in range(167):
            chunk = await microphone.read_chunk()
            audio_buffer.append(chunk)

        print("[*] Recording finished. Stopping stream...")
        microphone.stop_stream()

        print("[*] Transcribing audio...")
        full_audio = b"".join(audio_buffer)
        result = await recognizer.transcribe_audio(full_audio)

        print("\n========================================")
        print(f"Transcription: '{result.text}'")
        print(f"Confidence: {result.confidence:.2f}")
        print(f"Language: {result.language}")
        print(f"Duration: {result.duration:.2f}s")
        print("========================================\n")

    try:
        asyncio.run(record_and_transcribe())
    except Exception as e:
        print(f"[-] Mic test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
