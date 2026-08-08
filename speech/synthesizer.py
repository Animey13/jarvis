"""
JARVIS Text-to-Speech (TTS) Synthesizer Module.

Implements the SpeechSynthesizer interface using Kokoro ONNX offline neural TTS.
Supports async execution queues, automatic model downloading, and graceful fallback.
"""

import asyncio
import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
import soundfile as sf

from speech.interfaces import SpeechSynthesizer

logger = logging.getLogger(__name__)

# Try to import kokoro safely, falling back to simulator if missing
try:
    from kokoro_onnx import Kokoro
    KOKORO_AVAILABLE = True
except ImportError:
    logger.warning("kokoro-onnx is not fully installed. Falling back to simulator subtitles.")
    KOKORO_AVAILABLE = False


class PiperSynthesizer(SpeechSynthesizer):
    """
    Offline Text-to-Speech engine utilizing the lightweight, high-quality Kokoro ONNX model.
    Maintains existing Class Name (PiperSynthesizer) and interface to preserve backward compatibility.
    """

    def __init__(
        self,
        voice: str = "af_heart",
        speed: float = 1.0,
        piper_path: str = "piper",
        use_simulator: bool = False
    ) -> None:
        """
        Initializes the Kokoro Synthesizer (retaining signature of PiperSynthesizer).

        Args:
            voice: Name of the Kokoro voice (e.g. 'af_heart', 'af_sarah'). Maps old defaults automatically.
            speed: Speaking speed multiplier.
            piper_path: Legacy argument preserved for compatibility.
            use_simulator: Force mock speech (subtitles) without invoking system audio players.
        """
        rate = int(150 * speed)
        super().__init__(voice_id=voice, rate=rate)

        # Map legacy default voice to a high-quality Kokoro default voice
        self.voice_model: str = voice
        if "lessac" in voice or voice == "en_US-lessac-medium" or voice == "default":
            self.voice_model = "af_heart"
            logger.info("Mapped legacy default Piper voice to Kokoro default voice '%s'", self.voice_model)

        self.speed: float = speed
        self.use_simulator: bool = use_simulator or not KOKORO_AVAILABLE
        self.console: Console = Console()

        # Temp directories for rendering WAVs
        self._temp_dir = Path("/tmp/jarvis_tts")
        try:
            self._temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            self._temp_dir = Path(".")

        # Initialize assets directory and target model paths
        from config.config import BASE_DIR
        self._assets_dir = BASE_DIR / "assets"
        self._assets_dir.mkdir(parents=True, exist_ok=True)

        self.model_path = self._assets_dir / "kokoro-v1.0.int8.onnx"
        self.voices_path = self._assets_dir / "voices-v1.0.bin"

        # Queuing mechanism for multiple responses
        self._speech_queue: asyncio.Queue[str] = asyncio.Queue()
        self._current_process: Optional[subprocess.Popen[bytes]] = None
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._is_playing: bool = False

        self.kokoro: Optional[Any] = None

        if not self.use_simulator:
            # Ensure model files are downloaded locally, then initialize engine
            self._ensure_kokoro_files_exist()
            try:
                if KOKORO_AVAILABLE and self.model_path.exists() and self.voices_path.exists():
                    self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))
                    logger.info("Kokoro ONNX Engine initialized successfully with model '%s'", self.model_path.name)
                else:
                    logger.warning("Kokoro model files are missing. Falling back to simulator subtitles.")
                    self.use_simulator = True
            except Exception as e:
                logger.error("Failed to initialize Kokoro ONNX engine: %s. Toggling simulator subtitles.", e)
                self.use_simulator = True

        # Start background task queue consumer
        self._start_queue_worker()

        logger.info(
            "PiperSynthesizer (Kokoro TTS Backend) initialized (Voice: '%s', Speed: %.1fx, Simulator: %s)",
            self.voice_model, self.speed, self.use_simulator
        )

    def _ensure_kokoro_files_exist(self) -> None:
        """
        Verifies and automatically downloads the Kokoro model and voice files if missing.
        """
        import urllib.request

        model_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx"
        voices_url = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

        try:
            if not self.model_path.exists():
                logger.info("Kokoro model file missing. Downloading %s to %s...", model_url, self.model_path)
                print("[*] Downloading Kokoro TTS model weights (~80MB)... Please wait.")
                urllib.request.urlretrieve(model_url, self.model_path)
                logger.info("Successfully downloaded Kokoro model file.")

            if not self.voices_path.exists():
                logger.info("Kokoro voices bin file missing. Downloading %s to %s...", voices_url, self.voices_path)
                print("[*] Downloading Kokoro voice configurations (~27MB)... Please wait.")
                urllib.request.urlretrieve(voices_url, self.voices_path)
                logger.info("Successfully downloaded Kokoro voices bin.")

        except Exception as e:
            logger.error("Failed to download Kokoro TTS resources: %s. Offline mode fallback activated.", e)

    def _start_queue_worker(self) -> None:
        """Starts the background coroutine that monitors and plays queued speech items."""
        try:
            loop = asyncio.get_running_loop()
            self._worker_task = loop.create_task(self._queue_worker())
        except RuntimeError:
            logger.debug("No running event loop. Background speech worker deferred.")

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

        while not self._speech_queue.empty():
            try:
                self._speech_queue.get_nowait()
                self._speech_queue.task_done()
            except asyncio.QueueEmpty:
                break

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
        if self._worker_task is None or self._worker_task.done():
            self._start_queue_worker()
        await self._speech_queue.put(text)
        logger.debug("Text queued for synthesis: '%s'", text)

    async def _synthesize_and_play(self, text: str) -> None:
        """
        Performs the actual synthesis of text into speech using Kokoro-ONNX and plays the audio.
        """
        logger.info("TTS [text received]: '%s'", text)

        # 1. Simulator fallback: display subtitles on console
        if self.use_simulator or self.kokoro is None:
            logger.info("TTS [playback backend selected]: 'Simulated subtitles'")
            await self._simulate_speech(text)
            logger.info("TTS [playback completed].")
            return

        logger.info("TTS [voice model path]: '%s'", self.model_path)
        wav_path = self._temp_dir / f"tts_{hash(text) & 0xFFFFFFFF}.wav"

        # 2. Kokoro Synthesis to numpy buffer
        logger.info("TTS [synthesis started].")
        loop = asyncio.get_running_loop()

        try:
            # Map Kokoro-ONNX compatible language codes based on voice name prefixes
            # e.g., 'a' prefix stands for American English (en-us), 'b' stands for British English (en-gb)
            lang = "en-us"
            if self.voice_model.startswith("b"):
                lang = "en-gb"
            elif self.voice_model.startswith("j"):
                lang = "ja"
            elif self.voice_model.startswith("z"):
                lang = "zh"
            elif self.voice_model.startswith("e"):
                lang = "es"
            elif self.voice_model.startswith("f"):
                lang = "fr"
            elif self.voice_model.startswith("i"):
                lang = "it"
            elif self.voice_model.startswith("p"):
                lang = "pt"

            # Execute model inference in thread pool executor to prevent stalling the main event loop
            samples, sample_rate = await loop.run_in_executor(
                None,
                lambda: self.kokoro.create(
                    text=text,
                    voice=self.voice_model,
                    speed=self.speed,
                    lang=lang
                )
            )

            # Write numpy floats directly to wav file using soundfile
            await loop.run_in_executor(
                None,
                lambda: sf.write(str(wav_path), samples, sample_rate)
            )

            logger.info("TTS [synthesis finished].")
            logger.info("TTS [WAV output path]: '%s'", wav_path)

        except Exception as e:
            logger.error("Kokoro synthesis failed: %s. Falling back to simulator subtitles.", e)
            logger.info("TTS [playback backend selected]: 'Simulated subtitles'")
            await self._simulate_speech(text)
            logger.info("TTS [playback completed].")
            return

        # 3. Audio playback
        player_cmd: Optional[List[str]] = None
        backend_name: str = "none"

        # Candidate Ubuntu standard audio players
        for candidate in ["aplay", "paplay", "play", "ffplay"]:
            try:
                subprocess.run([candidate, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                backend_name = candidate
                if candidate == "ffplay":
                    player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_path)]
                elif candidate == "aplay":
                    player_cmd = ["aplay", "-q", str(wav_path)]
                else:
                    player_cmd = [candidate, str(wav_path)]
                break
            except FileNotFoundError:
                continue

        if not player_cmd:
            logger.warning("No compatible Ubuntu command-line player (aplay/paplay/ffplay) detected. Toggling simulator subtitles.")
            self.use_simulator = True
            logger.info("TTS [playback backend selected]: 'Simulated subtitles'")
            await self._simulate_speech(text)
            logger.info("TTS [playback completed].")
            return

        logger.info("TTS [playback backend selected]: '%s'", backend_name)

        try:
            logger.debug("Executing player command: %s", " ".join(player_cmd))

            # Start player process
            play_proc = subprocess.Popen(
                player_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self._current_process = play_proc

            # Wait for player process asynchronously
            while play_proc.poll() is None:
                await asyncio.sleep(0.05)

            stdout_play, stderr_play = play_proc.communicate()

            if play_proc.returncode != 0:
                play_error_msg = (
                    f"CRITICAL: Audio playback backend failed with exit code {play_proc.returncode}.\n"
                    f"STDOUT:\n{stdout_play.decode().strip()}\n"
                    f"STDERR:\n{stderr_play.decode().strip()}"
                )
                print(play_error_msg)
                logger.error(play_error_msg)
            else:
                logger.info("TTS [playback completed].")

        except Exception as e:
            logger.error("Error during speech audio playback execution: %s", e)
        finally:
            self._current_process = None
            try:
                if wav_path.exists():
                    wav_path.unlink()
            except Exception:
                pass

    async def _simulate_speech(self, text: str) -> None:
        """Mock speaker: Displays colored terminal subtitles with phonetic speaking delays."""
        self.console.print(f"\n🗣️  [bold yellow]JARVIS speaking:[/bold yellow] [italic white]\"{text}\"[/italic white]\n")
        reading_delay = len(text) / 15.0
        delay = min(max(reading_delay, 0.5), 5.0)
        await asyncio.sleep(delay)

    def __del__(self) -> None:
        """Lifecycle destructor: cleans up background tasks and temporary WAVs."""
        if self._worker_task:
            self._worker_task.cancel()
        try:
            for file in self._temp_dir.glob("tts_*.wav"):
                file.unlink()
        except Exception:
            pass
