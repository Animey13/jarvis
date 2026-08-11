"""
JARVIS Speech Orchestration Manager.

Coordinates MicrophoneManager, WakeWordEngine, FasterWhisperRecognizer, and PiperSynthesizer
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
from speech.synthesizer import PiperSynthesizer
from speech.wakeword import WakeWordEngine

logger = logging.getLogger(__name__)


class SpeechManager:
    """
    Central manager that orchestrates JARVIS's voice-in and voice-out loop.
    Implements a robust state machine for wake word spotting, VAD-based recording,
    Whisper transcription, and Piper TTS synthesis.
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
        tts_provider = settings.speech.tts_provider.lower()
        if tts_provider in ("kokoro", "local"):
            from speech.synthesizer import KokoroSynthesizer
            self.synthesizer = KokoroSynthesizer(
                voice=settings.speech.voice_id,
                speed=settings.kokoro.speed,
                model_filename=settings.kokoro.model,
                voices_filename=settings.kokoro.voices,
                use_simulator=settings.kokoro.use_simulator
            )
        else:
            from speech.synthesizer import PiperSynthesizer
            self.synthesizer = PiperSynthesizer(
                voice=settings.piper.voice,
                speed=settings.piper.speed,
                piper_path=settings.piper.piper_path,
                use_simulator=settings.piper.use_simulator
            )

        self.console = Console()

        # State flags
        self.is_running: bool = False
        self._loop_task: Optional[asyncio.Task[None]] = None

        # User defined speech callback (async func taking user prompt, returning response)
        self._speech_callback: Optional[Callable[[str], Awaitable[str]]] = None

        logger.info("SpeechManager successfully initialized.")

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

        # Keep a history of VAD states to optimize wake detection
        recent_activity_count = 0

        while self.is_running:
            try:
                # Read 30ms of audio frame from the microphone
                chunk = await self.microphone.read_chunk()

                # Run voice activity check on chunk
                is_voice = self.recognizer.is_speech(chunk)

                if current_state == "WAKING":
                    # --- STATE 1: Gated Wake Word Detection ---
                    # To minimize CPU load, we only accumulate frames if there is active sound
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
                    # Let's run Whisper check if the buffer is reasonably populated and activity has quieted down
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

                            # Transition state
                            current_state = "LISTENING"
                            active_speech_buffer.clear()
                            silence_start_time = None
                            speech_started = False
                            speech_start_time = None

                elif current_state == "LISTENING":
                    # --- STATE 2: User Voice Activity Recording ---
                    active_speech_buffer.append(chunk)

                    if is_voice:
                        # User is speaking
                        if not speech_started:
                            logger.debug("Active user speech started.")
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
                                if elapsed_silence >= self.recognizer.silence_timeout:
                                    # User has finished speaking!
                                    elapsed_speech = time.time() - speech_start_time
                                    logger.info("VAD: Silence timeout reached. Total speaking duration: %.2fs", elapsed_speech)

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

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in SpeechManager execution loop: %s", e)
                await asyncio.sleep(0.1)  # Prevent tight error looping
