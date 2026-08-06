"""
JARVIS Text-to-Speech (TTS) Synthesizer Module.

Implements the SpeechSynthesizer interface using Piper offline neural TTS.
Supports async execution queues, concurrent speech cancellation, and graceful fallback.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console

from speech.interfaces import SpeechSynthesizer

logger = logging.getLogger(__name__)


class PiperSynthesizer(SpeechSynthesizer):
    """
    Offline Text-to-Speech engine utilizing the fast neural Piper TTS system.
    Supports response queuing, speed modulation, and immediate audio interruption.
    """

    def __init__(
        self,
        voice: str = "en_US-lessac-medium",
        speed: float = 1.0,
        piper_path: str = "piper",
        use_simulator: bool = False
    ) -> None:
        """
        Initializes the PiperSynthesizer.

        Args:
            voice: Name or file path of the Piper ONNX voice model.
            speed: Speaking speed multiplier.
            piper_path: Path to the piper executable on the system.
            use_simulator: Force mock speech (subtitles) without invoking system audio players.
        """
        # Convert speed multiplier to a voice rate (WPM fallback from Phase 1 interface)
        rate = int(150 * speed)
        super().__init__(voice_id=voice, rate=rate)

        self.voice_model: str = voice
        self.speed: float = speed
        self.piper_path: str = piper_path
        self.use_simulator: bool = use_simulator
        self.console: Console = Console()

        # Queuing mechanism for multiple responses
        self._speech_queue: asyncio.Queue[str] = asyncio.Queue()
        self._current_process: Optional[subprocess.Popen[bytes]] = None
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._is_playing: bool = False

        # Temp directories for rendering WAVs
        self._temp_dir = Path("/tmp/jarvis_tts")
        try:
            self._temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            self._temp_dir = Path(".")

        # Start the background speech queue consumer
        self._start_queue_worker()

        logger.info(
            "PiperSynthesizer initialized (Voice: '%s', Speed: %.1fx, Piper: '%s', Simulator: %s)",
            self.voice_model, self.speed, self.piper_path, self.use_simulator
        )

    def _start_queue_worker(self) -> None:
        """Starts the background coroutine that monitors and plays queued speech items."""
        self._worker_task = asyncio.create_task(self._queue_worker())

    async def _queue_worker(self) -> None:
        """Background loop consuming texts from the queue sequentially."""
        while True:
            text = None
            try:
                text = await self._speech_queue.get()
                self._is_playing = True
                await self._synthesize_and_play(text)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error in TTS queue worker loop: %s", e)
            finally:
                self._is_playing = False
                if text is not None:
                    self._speech_queue.task_done()

    def stop(self) -> None:
        """
        Interrupts and immediately stops any ongoing speech playback.
        Clears any pending texts in the speech queue.
        """
        logger.info("Speech interruption requested. Stopping playback and clearing queues.")

        # Clear the queue
        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except asyncio.QueueEmpty:
                break

        # Terminate active audio process
        if self._current_process:
            try:
                logger.info("Terminating active playback process PID %d.", self._current_process.pid)
                self._current_process.terminate()
                self._current_process.wait(timeout=0.5)
            except Exception as e:
                logger.debug("Failed to cleanly terminate speech process: %s. Forcing kill.", e)
                if self._current_process:
                    try:
                        self._current_process.kill()
                    except Exception:
                        pass
            finally:
                self._current_process = None

    async def speak(self, text: str) -> None:
        """
        Directly speaks the text, bypassing and clearing the queue.
        Interrupts any existing speech before starting.

        Args:
            text: Text block to synthesize and speak.
        """
        self.stop()
        await self.speak_queued(text)

    async def speak_queued(self, text: str) -> None:
        """
        Adds text to the playback queue to be played in FIFO order.

        Args:
            text: Text block to synthesize and queue.
        """
        if not text.strip():
            return
        await self._speech_queue.put(text)
        logger.debug("Text queued for synthesis: '%s'", text)

    async def _synthesize_and_play(self, text: str) -> None:
        """
        Performs the actual synthesis of text into speech, with subprocess rendering
        and platform audio player fallback.
        """
        logger.info("TTS Synthesis started: '%s'", text)

        # Ensure correct temporary output path
        wav_path = self._temp_dir / f"tts_{hash(text) & 0xFFFFFFFF}.wav"

        # 1. Simulator fallback: display subtitles on console
        if self.use_simulator:
            await self._simulate_speech(text)
            return

        # 2. Piper rendering to wav file
        # Command form: echo "text" | piper --model voice.onnx --output_file file.wav --length_scale (1/speed)
        length_scale = 1.0 / self.speed if self.speed > 0 else 1.0

        # Look for the voice model. If it's a relative path or name, we look in 'assets/' or 'config/'
        model_path = self.voice_model
        if not Path(model_path).exists():
            # Check standard path
            from config.config import BASE_DIR
            assets_model = BASE_DIR / "assets" / f"{self.voice_model}.onnx"
            if assets_model.exists():
                model_path = str(assets_model)

        piper_cmd = [
            self.piper_path,
            "--model", model_path,
            "--output_file", str(wav_path),
            "--length_scale", f"{length_scale:.2f}"
        ]

        logger.debug("Running Piper command: %s", " ".join(piper_cmd))
        loop = asyncio.get_running_loop()

        try:
            # Run Piper in background process to keep thread non-blocking
            piper_proc = await asyncio.create_subprocess_exec(
                *piper_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE
            )

            stdout, stderr = await piper_proc.communicate(input=text.encode("utf-8"))

            if piper_proc.returncode != 0:
                logger.error("Piper synthesis failed with exit code %d: %s", piper_proc.returncode, stderr.decode().strip())
                raise RuntimeError("Piper binary error")

        except Exception as e:
            logger.warning("Piper is not executable or voice model missing: %s. Falling back to simulator mode.", e)
            self.use_simulator = True
            await self._simulate_speech(text)
            return

        # 3. Audio playback
        # We look for a system-level player to play the generated wav file on Ubuntu.
        # Standard Ubuntu players: aplay, paplay, play (sox), ffplay (ffmpeg)
        player_cmd: Optional[List[str]] = None
        for candidate in ["aplay", "paplay", "play", "ffplay"]:
            # Check if command exists
            try:
                subprocess.run([candidate, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if candidate == "ffplay":
                    player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_path)]
                elif candidate == "aplay":
                    # aplay is standard ALSA player
                    player_cmd = ["aplay", "-q", str(wav_path)]
                else:
                    player_cmd = [candidate, str(wav_path)]
                break
            except FileNotFoundError:
                continue

        if not player_cmd:
            logger.warning("No compatible Ubuntu command-line player (aplay/paplay/ffplay) detected. Toggling simulator.")
            self.use_simulator = True
            await self._simulate_speech(text)
            return

        try:
            # Start playing wav file
            logger.debug("Executing player command: %s", " ".join(player_cmd))
            # Start player using python subprocess Popen (stored in self._current_process for quick interrupts)
            play_proc = subprocess.Popen(player_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._current_process = play_proc

            # Wait for player process to complete asynchronously
            while play_proc.poll() is None:
                await asyncio.sleep(0.05)

            logger.info("Speech playback completed successfully.")

        except Exception as e:
            logger.error("Error during speech audio playback: %s", e)
        finally:
            self._current_process = None
            # Safely clean up temporary WAV file
            try:
                if wav_path.exists():
                    wav_path.unlink()
            except Exception:
                pass

    async def _simulate_speech(self, text: str) -> None:
        """Mock speaker: Displays colored terminal subtitles with phonetic speaking delays."""
        self.console.print(f"\n🗣️  [bold yellow]JARVIS speaking:[/bold yellow] [italic white]\"{text}\"[/italic white]\n")
        # Approximate reading speed: 15 characters per second
        reading_delay = len(text) / 15.0
        # Cap simulated delay between 0.5s and 5s
        delay = min(max(reading_delay, 0.5), 5.0)
        await asyncio.sleep(delay)

    def __del__(self) -> None:
        """Lifecycle destructor: cleans up background tasks and temporary WAVs."""
        if self._worker_task:
            self._worker_task.cancel()
        try:
            # Clean up temp files
            for file in self._temp_dir.glob("tts_*.wav"):
                file.unlink()
        except Exception:
            pass
