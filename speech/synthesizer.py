"""
JARVIS Text-to-Speech (TTS) Synthesizer Module.

Provides both Piper (subprocess-based) and Kokoro (ONNX-based) synthesizer backends,
adhering to the common SpeechSynthesizer interface.
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
    Offline Text-to-Speech engine utilizing the Rhasspy Piper TTS binary.
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
        rate = int(150 * speed)
        super().__init__(voice_id=voice, rate=rate)

        self.voice_model: str = voice
        self.speed: float = speed
        self.piper_path: str = piper_path
        self.use_simulator: bool = use_simulator
        self.console: Console = Console()

        # Check if the piper executable supports Piper arguments (only if not using simulator explicitly)
        self._is_piper_valid: bool = False
        if not self.use_simulator:
            self._is_piper_valid = self._is_valid_piper_executable(self.piper_path)
            if not self._is_piper_valid:
                print("Rhasspy Piper TTS executable not found.")
                logger.warning(
                    "Rhasspy Piper TTS executable '%s' not found or invalid. Falling back to simulator subtitles.",
                    self.piper_path
                )
                self.use_simulator = True
        else:
            self._is_piper_valid = False

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
            "PiperSynthesizer initialized (Voice: '%s', Speed: %.1fx, Piper: '%s', Simulator: %s, Valid: %s)",
            self.voice_model, self.speed, self.piper_path, self.use_simulator, self._is_piper_valid
        )

    def _is_valid_piper_executable(self, path: str) -> bool:
        """Verifies if the configured executable path points to a valid Rhasspy Piper TTS binary."""
        try:
            proc = subprocess.run(
                [path, "--help"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=2.0
            )
            help_output = proc.stdout + proc.stderr
            if "--model" in help_output:
                return True
        except Exception:
            pass
        return False

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
        """Interrupts and immediately stops any ongoing speech playback."""
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
        """Directly speaks the text, bypassing and clearing the queue."""
        self.stop()
        await self.speak_queued(text)

    async def speak_queued(self, text: str) -> None:
        """Adds text to the playback queue to be played in FIFO order."""
        if not text.strip():
            return
        if self._worker_task is None or self._worker_task.done():
            self._start_queue_worker()
        await self._speech_queue.put(text)
        logger.debug("Text queued for synthesis: '%s'", text)

    def _ensure_voice_model_exists(self) -> str:
        """Ensures that the Piper voice model ONNX file and its JSON configuration exist locally."""
        from config.config import BASE_DIR
        assets_dir = BASE_DIR / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        if Path(self.voice_model).exists():
            return str(Path(self.voice_model).resolve())

        onnx_path = assets_dir / f"{self.voice_model}.onnx"
        json_path = assets_dir / f"{self.voice_model}.onnx.json"

        if not onnx_path.exists() or not json_path.exists():
            logger.info("Voice model '%s' not found locally. Starting download...", self.voice_model)
            import urllib.request
            parts = self.voice_model.split("-")
            if len(parts) >= 2:
                lang_code = parts[0].split("_")[0]
                country_code = parts[0]
                voice_name = parts[1]
                quality = parts[2] if len(parts) > 2 else "medium"

                base_url = f"https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/{lang_code}/{country_code}/{voice_name}/{quality}"
                onnx_url = f"{base_url}/{self.voice_model}.onnx"
                json_url = f"{base_url}/{self.voice_model}.onnx.json"

                try:
                    urllib.request.urlretrieve(onnx_url, onnx_path)
                    urllib.request.urlretrieve(json_url, json_path)
                except Exception as e:
                    logger.error("Failed to automatically download voice model: %s", e)
        return str(onnx_path.resolve())

    async def _synthesize_and_play(self, text: str) -> None:
        """Performs actual synthesis and playback via Piper command CLI."""
        logger.info("TTS [text received]: '%s'", text)
        logger.info("TTS [Piper executable]: '%s'", self.piper_path)

        if self.use_simulator or not self._is_piper_valid:
            logger.info("TTS [playback backend selected]: 'Simulated subtitles'")
            await self._simulate_speech(text)
            logger.info("TTS [playback completed].")
            return

        model_path = self._ensure_voice_model_exists()
        logger.info("TTS [voice model path]: '%s'", model_path)

        wav_path = self._temp_dir / f"tts_{hash(text) & 0xFFFFFFFF}.wav"
        length_scale = 1.0 / self.speed if self.speed > 0 else 1.0

        piper_cmd = [
            self.piper_path,
            "--model", model_path,
            "--output_file", str(wav_path),
            "--length_scale", f"{length_scale:.2f}"
        ]

        logger.info("TTS [synthesis started]. Command: %s", " ".join(piper_cmd))
        loop = asyncio.get_running_loop()

        try:
            text_input = text + "\n"
            piper_proc = await asyncio.create_subprocess_exec(
                *piper_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await piper_proc.communicate(input=text_input.encode("utf-8"))

            if piper_proc.returncode != 0:
                error_msg = f"CRITICAL: Piper synthesis failed.\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}"
                print(error_msg)
                logger.error(error_msg)
                raise RuntimeError("Piper binary error")

            logger.info("TTS [synthesis finished].")
            logger.info("TTS [WAV output path]: '%s'", wav_path)

        except Exception as e:
            logger.warning("Piper invocation failed: %s. Falling back to simulator subtitles.", e)
            self.use_simulator = True
            await self._simulate_speech(text)
            return

        # Play WAV using standard OS players
        player_cmd: Optional[List[str]] = None
        backend_name: str = "none"
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
            logger.warning("No compatible Ubuntu command-line player detected. Toggling simulator subtitles.")
            self.use_simulator = True
            await self._simulate_speech(text)
            return

        logger.info("TTS [playback backend selected]: '%s'", backend_name)

        try:
            play_proc = subprocess.Popen(player_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self._current_process = play_proc

            while play_proc.poll() is None:
                await asyncio.sleep(0.05)

            stdout_play, stderr_play = play_proc.communicate()
            if play_proc.returncode != 0:
                print(f"CRITICAL: Playback failed.\nSTDOUT: {stdout_play.decode()}\nSTDERR: {stderr_play.decode()}")
            else:
                logger.info("TTS [playback completed].")
        except Exception as e:
            logger.error("Error playing audio: %s", e)
        finally:
            self._current_process = None
            try:
                if wav_path.exists():
                    wav_path.unlink()
            except Exception:
                pass

    async def _simulate_speech(self, text: str) -> None:
        self.console.print(f"\n🗣️  [bold yellow]JARVIS speaking:[/bold yellow] [italic white]\"{text}\"[/italic white]\n")
        await asyncio.sleep(min(max(len(text) / 15.0, 0.5), 5.0))


class KokoroSynthesizer(SpeechSynthesizer):
    """
    Offline Text-to-Speech engine utilizing the state-of-the-art Kokoro ONNX model.
    """

    def __init__(
        self,
        voice: str = "af_heart",
        speed: float = 1.0,
        model_filename: str = "kokoro-v1.0.fp16.onnx",
        voices_filename: str = "voices-v1.0.bin",
        use_simulator: bool = False
    ) -> None:
        """
        Initializes the KokoroSynthesizer.

        Args:
            voice: Name of the Kokoro voice (e.g. 'af_heart', 'af_sarah').
            speed: Speaking speed multiplier.
            model_filename: File name of the Kokoro ONNX model weights in assets/.
            voices_filename: File name of the Kokoro voices bin in assets/.
            use_simulator: Force mock speech (subtitles) without invoking system audio players.
        """
        rate = int(150 * speed)
        super().__init__(voice_id=voice, rate=rate)

        self.voice_model: str = voice
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

        self.model_path = self._assets_dir / model_filename
        self.voices_path = self._assets_dir / voices_filename

        # Gated fallback check for missing model/voice assets (Requirement 13)
        self._is_assets_valid: bool = True
        if not self.use_simulator:
            # Fallback for local sandbox testing where we have int8 model
            if not self.model_path.exists() and (self._assets_dir / "kokoro-v1.0.int8.onnx").exists():
                self.model_path = self._assets_dir / "kokoro-v1.0.int8.onnx"
                logger.info("Voice asset fallback: using local int8 model %s.", self.model_path.name)

            if not self.model_path.exists() or not self.voices_path.exists():
                self._is_assets_valid = False
                logger.warning(
                    "Kokoro model assets missing (Model: %s, Voices: %s). Falling back to simulator subtitles.",
                    self.model_path, self.voices_path
                )
                self.use_simulator = True

        # Queuing mechanism for multiple responses
        self._speech_queue: asyncio.Queue[str] = asyncio.Queue()
        self._current_process: Optional[subprocess.Popen[bytes]] = None
        self._worker_task: Optional[asyncio.Task[None]] = None
        self._is_playing: bool = False

        self.kokoro: Optional[Any] = None

        if not self.use_simulator and self._is_assets_valid:
            try:
                self.kokoro = Kokoro(str(self.model_path), str(self.voices_path))
                logger.info("Kokoro ONNX Engine initialized successfully with model '%s'", self.model_path.name)
            except Exception as e:
                logger.error("Failed to initialize Kokoro ONNX engine: %s. Toggling simulator subtitles.", e)
                self.use_simulator = True

        # Start background task queue consumer
        self._start_queue_worker()

        logger.info(
            "KokoroSynthesizer initialized (Voice: '%s', Speed: %.1fx, Simulator: %s, Valid Assets: %s)",
            self.voice_model, self.speed, self.use_simulator, self._is_assets_valid
        )

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
        """Interrupts and immediately stops any ongoing speech playback."""
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
        """Directly speaks the text, bypassing and clearing the queue."""
        self.stop()
        await self.speak_queued(text)

    async def speak_queued(self, text: str) -> None:
        """Adds text to the playback queue to be played in FIFO order."""
        if not text.strip():
            return
        if self._worker_task is None or self._worker_task.done():
            self._start_queue_worker()
        await self._speech_queue.put(text)
        logger.debug("Text queued for synthesis: '%s'", text)

    async def _synthesize_and_play(self, text: str) -> None:
        """Performs actual Kokoro synthesis and audio playback."""
        # Requirements: Log every stage
        # - text received
        # - voice model path
        # - synthesis started
        # - synthesis finished
        # - WAV output path
        # - playback backend selected
        # - playback completed
        logger.info("TTS [text received]: '%s'", text)

        if self.use_simulator or self.kokoro is None:
            logger.info("TTS [playback backend selected]: 'Simulated subtitles'")
            await self._simulate_speech(text)
            logger.info("TTS [playback completed].")
            return

        logger.info("TTS [voice model path]: '%s'", self.model_path)
        wav_path = self._temp_dir / f"tts_{hash(text) & 0xFFFFFFFF}.wav"

        logger.info("TTS [synthesis started].")
        loop = asyncio.get_running_loop()

        try:
            # Map Kokoro-ONNX language code prefixes
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

            samples, sample_rate = await loop.run_in_executor(
                None,
                lambda: self.kokoro.create(
                    text=text,
                    voice=self.voice_model,
                    speed=self.speed,
                    lang=lang
                )
            )

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

        player_cmd: Optional[List[str]] = None
        backend_name: str = "none"

        # Enforce paplay as the preferred player if available, then fallback to other standard candidates
        for candidate in ["paplay", "aplay", "play", "ffplay"]:
            try:
                subprocess.run([candidate, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                backend_name = candidate
                if candidate == "ffplay":
                    player_cmd = ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", str(wav_path)]
                elif candidate == "aplay":
                    player_cmd = ["aplay", "-q", str(wav_path)]
                elif candidate == "paplay":
                    player_cmd = ["paplay", str(wav_path)]
                else:
                    player_cmd = [candidate, str(wav_path)]
                break
            except FileNotFoundError:
                continue

        if not player_cmd:
            logger.warning("No compatible command-line player detected. Toggling simulator subtitles.")
            self.use_simulator = True
            logger.info("TTS [playback backend selected]: 'Simulated subtitles'")
            await self._simulate_speech(text)
            logger.info("TTS [playback completed].")
            return

        logger.info("TTS [playback backend selected]: '%s'", backend_name)

        try:
            logger.debug("Executing player command: %s", " ".join(player_cmd))

            play_proc = subprocess.Popen(
                player_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self._current_process = play_proc

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
        await asyncio.sleep(min(max(len(text) / 15.0, 0.5), 5.0))

    def __del__(self) -> None:
        """Lifecycle destructor."""
        if self._worker_task:
            self._worker_task.cancel()
        try:
            for file in self._temp_dir.glob("tts_*.wav"):
                file.unlink()
        except Exception:
            pass
