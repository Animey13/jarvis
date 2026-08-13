"""
JARVIS Speech Orchestration Manager.

Coordinates MicrophoneManager, WakeWordEngine, FasterWhisperRecognizer, and PiperSynthesizer/KokoroSynthesizer
into a unified, stateful, and reactive speech interaction layer.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Awaitable

from rich.console import Console
from config.config import Settings
from speech.microphone import MicrophoneManager
from speech.recognizer import FasterWhisperRecognizer
from speech.synthesizer import PiperSynthesizer, KokoroSynthesizer
from speech.wakeword import WakeWordEngine

logger = logging.getLogger(__name__)


class SpeechManager:
    """
    Central manager that orchestrates JARVIS's voice-in and voice-out loop.
    Implements a robust state machine for wake word spotting, VAD-based recording,
    Whisper transcription, and local TTS synthesis.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initializes the SpeechManager and its coordinated components.

        Args:
            settings: Loaded global system configuration settings.
        """
        self.settings: Settings = settings

        # 1. Initialize Microphone Manager
        self.microphone = MicrophoneManager(
            device=settings.microphone.device,
            sample_rate=settings.microphone.sample_rate,
            channels=settings.microphone.channels,
            use_simulator=settings.microphone.use_simulator
        )

        # 2. Initialize Wake Word Engine
        self.wakeword = WakeWordEngine(
            phrase=settings.wakeword.phrase,
            cooldown=settings.wakeword.cooldown,
            ignore_accidental_probability=settings.wakeword.ignore_accidental_probability
        )

        # 3. Initialize Faster Whisper STT Recognizer
        self.recognizer = FasterWhisperRecognizer(
            model_name=settings.whisper.model,
            language=settings.whisper.language,
            compute_type=settings.whisper.compute_type,
            use_gpu=settings.whisper.use_gpu,
            vad_sensitivity=settings.vad.sensitivity,
            silence_timeout=settings.vad.silence_timeout,
            min_speech_duration=settings.vad.min_speech_duration,
            device_name=settings.microphone.device
        )

        # 4. Initialize TTS Synthesizer based on provider
        # Defaults to Kokoro unless Piper is explicitly configured
        tts_provider = settings.speech.tts_provider.lower()
        if tts_provider == "piper":
            self.synthesizer = PiperSynthesizer(
                voice=settings.piper.voice,
                speed=settings.piper.speed,
                piper_path=settings.piper.piper_path,
                use_simulator=settings.piper.use_simulator
            )
        else:
            self.synthesizer = KokoroSynthesizer(
                voice=settings.speech.voice_id,
                speed=settings.kokoro.speed,
                model_filename=settings.kokoro.model,
                voices_filename=settings.kokoro.voices,
                use_simulator=settings.kokoro.use_simulator
            )

        self.console = Console()

        # State flags
        self.is_running: bool = False
        self._loop_task: Optional[asyncio.Task[None]] = None

        # User defined speech callback (async func taking user prompt, returning response)
        self._speech_callback: Optional[Callable[[str], Awaitable[str]]] = None

        logger.info("SpeechManager successfully initialized with backend: %s", self.synthesizer.__class__.__name__)

    def register_speech_callback(self, callback: Callable[[str], Awaitable[str]]) -> None:
        """
        Registers an asynchronous callback to process transcribed user speech.

        Args:
            callback: Async function taking transcribed text (str) and returning response (str).
        """
        self._speech_callback = callback
        logger.info("User speech callback registered successfully.")

    async def start(self) -> None:
        """
        Starts the background speech orchestration loop.
        """
        if self.is_running:
            logger.warning("SpeechManager is already running.")
            return

        self.is_running = True
        self.microphone.start_stream()
        self._loop_task = asyncio.create_task(self._run_orchestration_loop())
        logger.info("SpeechManager started background audio-loop.")

    async def stop(self) -> None:
        """
        Stops the speech manager, releases microphone stream, and halts background loops.
        """
        if not self.is_running:
            return

        logger.info("Stopping SpeechManager subsystems...")
        self.is_running = False

        if self._loop_task:
            self._loop_task.cancel()
            try:
                await self._loop_task
            except asyncio.CancelledError:
                pass
            self._loop_task = None

        self.microphone.stop_stream()
        self.synthesizer.stop()
        logger.info("SpeechManager stopped successfully.")

    async def _run_orchestration_loop(self) -> None:
        """
        Primary asynchronous loop running the speech state machine.
        """
        logger.info("Entering SpeechManager orchestration state loop.")

        # States: "WAKING" (waiting for Jarvis), "LISTENING" (recording active prompt)
        current_state = "WAKING"

        # Audio accumulator buffers
        rolling_wake_buffer: List[bytes] = []
        active_speech_buffer: List[bytes] = []

        # Tracking active timers for silence detection
        silence_start_time: Optional[float] = None
        speech_started = False
        speech_start_time: Optional[float] = None
        listening_entry_time: Optional[float] = None

        # State tracking for wake activity gating
        recent_activity_count = 0

        while self.is_running:
            try:
                # Read 30ms of audio frame from the microphone
                chunk = await self.microphone.read_chunk()

                # Run voice activity check on chunk
                is_voice = self.recognizer.is_speech(chunk)

                if current_state == "WAKING":
                    # --- STATE 1: Gated Wake Word Detection ---
                    if is_voice:
                        rolling_wake_buffer.append(chunk)
                        recent_activity_count = 10  # Hold active state for next 10 frames (~300ms)
                    elif recent_activity_count > 0:
                        rolling_wake_buffer.append(chunk)
                        recent_activity_count -= 1

                    # Keep rolling wake buffer bounded at maximum 2 seconds (~66 frames)
                    if len(rolling_wake_buffer) > 66:
                        rolling_wake_buffer.pop(0)

                    # Periodically check if we accumulated enough audio and have voice activity
                    if len(rolling_wake_buffer) >= 20 and recent_activity_count == 0:
                        full_audio = b"".join(rolling_wake_buffer)
                        rolling_wake_buffer.clear()

                        # Fast transcribe in background
                        transcription = await self.recognizer.transcribe_audio(full_audio)

                        # Process wake word check
                        if self.wakeword.detect_in_text(transcription.text, transcription.confidence):
                            logger.info("Wake word triggered. Transiting to LISTENING state.")

                            # Play 'Listening...' subtitle & synthesize response
                            await self.synthesizer.speak("Listening")

                            # Wait until JARVIS finishes speaking "Listening" to prevent VAD self-triggering
                            while self.synthesizer.is_speaking:
                                await asyncio.sleep(0.05)

                            # Flush microphone queue to discard old accumulated frames and room echo
                            self.microphone.clear_queue()

                            # Transition state
                            current_state = "LISTENING"
                            active_speech_buffer.clear()
                            silence_start_time = None
                            speech_started = False
                            speech_start_time = None
                            listening_entry_time = time.time()

                elif current_state == "LISTENING":
                    # --- STATE 2: User Voice Activity Recording ---
                    active_speech_buffer.append(chunk)

                    if is_voice:
                        # User is speaking
                        if not speech_started:
                            logger.info("Active user speech started.")
                            speech_started = True
                            speech_start_time = time.time()
                        silence_start_time = None  # Reset silence timer
                    else:
                        # Silence detected
                        if speech_started:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            else:
                                elapsed_silence = time.time() - silence_start_time
                                elapsed_speech = time.time() - speech_start_time

                                # Terminate capture if silence interval exceeded OR maximum command duration (5.0s) reached
                                if elapsed_silence >= self.recognizer.silence_timeout or elapsed_speech >= 5.0:
                                    logger.info("VAD: Stop boundary reached. Silence: %.2fs, Speech: %.2fs", elapsed_silence, elapsed_speech)

                                    # Gating: check minimum speech duration
                                    if elapsed_speech >= self.recognizer.min_speech_duration:
                                        logger.info("Valid speech block captured. Starting transcription.")
                                        current_state = "TRANSCRIBING"

                                        # Process transcription
                                        full_audio_bytes = b"".join(active_speech_buffer)
                                        trans_result = await self.recognizer.transcribe_audio(full_audio_bytes)

                                        if trans_result.text.strip():
                                            self.console.print(f"[bold green]User prompt transcribed:[/bold green] [italic]'{trans_result.text}'[/italic]")

                                            # Invoke main prompt responder callback
                                            if self._speech_callback:
                                                response_text = await self._speech_callback(trans_result.text)
                                                if response_text:
                                                    await self.synthesizer.speak(response_text)
                                        else:
                                            logger.info("Transcribed audio yielded empty text. Discarding block.")
                                    else:
                                        logger.info("Captured speech segment was too short (%.2fs < %.2fs). Discarding.", elapsed_speech, self.recognizer.min_speech_duration)

                                    # Return to Waking state
                                    current_state = "WAKING"
                                    active_speech_buffer.clear()
                                    speech_started = False

                        else:
                            # If we haven't even started speaking, keep buffer size bounded to preserve pre-speech context (1.0s)
                            if len(active_speech_buffer) > 33:
                                active_speech_buffer.pop(0)

                    # Strict Safety Net: enforce maximum recording limit of 5.0 seconds even if VAD is continuously triggered
                    if speech_started and (time.time() - speech_start_time) >= 5.0:
                        logger.info("VAD: Maximum recording duration (5.0s) reached. Terminating recording.")
                        current_state = "TRANSCRIBING"

                        full_audio_bytes = b"".join(active_speech_buffer)
                        trans_result = await self.recognizer.transcribe_audio(full_audio_bytes)

                        if trans_result.text.strip():
                            self.console.print(f"[bold green]User prompt transcribed:[/bold green] [italic]'{trans_result.text}'[/italic]")
                            if self._speech_callback:
                                response_text = await self._speech_callback(trans_result.text)
                                if response_text:
                                    await self.synthesizer.speak(response_text)

                        current_state = "WAKING"
                        active_speech_buffer.clear()
                        speech_started = False

                    # Idle Safety Net: if the user does not speak at all within 5 seconds of entering LISTENING state, timeout and return to WAKING
                    if not speech_started and listening_entry_time and (time.time() - listening_entry_time) >= 5.0:
                        logger.info("VAD: Listening state idle timeout reached. Returning to WAKING.")
                        current_state = "WAKING"
                        active_speech_buffer.clear()
                        speech_started = False

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in SpeechManager execution loop: %s", e)
                await asyncio.sleep(0.1)  # Prevent tight error looping
