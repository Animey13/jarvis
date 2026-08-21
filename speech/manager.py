"""
JARVIS Speech Orchestration Manager Module.

Coordinates MicrophoneManager, WakeWordEngine, FasterWhisperRecognizer, and PiperSynthesizer/KokoroSynthesizer
into a formal, deterministic, reactive state machine for natural voice interaction.
"""

import asyncio
from enum import Enum
import logging
import time
from typing import Any, Awaitable, Callable, Dict, List, Optional

from rich.console import Console
from config.config import Settings
from speech.microphone import MicrophoneManager
from speech.recognizer import FasterWhisperRecognizer
from speech.synthesizer import KokoroSynthesizer, PiperSynthesizer
from speech.wakeword import WakeWordEngine

logger = logging.getLogger(__name__)


class SpeechState(Enum):
    """
    Formal state definitions for the JARVIS voice interaction state machine.
    """
    WAKING = "WAKING"
    LISTENING = "LISTENING"
    TRANSCRIBING = "TRANSCRIBING"
    THINKING = "THINKING"
    SPEAKING = "SPEAKING"
    INTERRUPTED = "INTERRUPTED"
    ERROR = "ERROR"
    SHUTDOWN = "SHUTDOWN"


class SpeechManager:
    """
    Central manager that orchestrates JARVIS's voice interaction loop.
    Implements a formal state machine for wake-word spotting, VAD-based recording,
    Whisper transcription, LLM orchestration, Kokoro TTS synthesis, and interruption handling.
    """

    def __init__(
        self,
        settings: Settings,
        listening_timeout: float = 5.0,
        maximum_command_duration: float = 5.0,
        interruption_sensitivity: int = 2
    ) -> None:
        """
        Initializes the SpeechManager and its coordinated components.

        Args:
            settings: Loaded global system configuration settings.
            listening_timeout: Idle duration in seconds allowed before returning to WAKING.
            maximum_command_duration: Maximum duration in seconds allowed for a single command.
            interruption_sensitivity: Number of consecutive speech frames required to trigger interruption.
        """
        self.settings: Settings = settings
        self.listening_timeout: float = listening_timeout
        self.maximum_command_duration: float = maximum_command_duration
        self.interruption_sensitivity: int = interruption_sensitivity

        # State tracking
        self.state: SpeechState = SpeechState.WAKING

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

        # State flags and task tracking
        self.is_running: bool = False
        self._loop_task: Optional[asyncio.Task[None]] = None
        self._active_speech_task: Optional[asyncio.Task[None]] = None

        # User defined speech callback
        self._speech_callback: Optional[Callable[[str], Awaitable[str]]] = None

        logger.info("SpeechManager successfully initialized with backend: %s", self.synthesizer.__class__.__name__)

    def transition_to(self, new_state: SpeechState) -> None:
        """
        Transitions the state machine to a new state with explicit logging.

        Args:
            new_state: Target SpeechState enum.
        """
        if self.state != new_state:
            logger.info("Speech State Transition: %s -> %s", self.state.value, new_state.value)
            self.state = new_state
            try:
                from web.state import event_bus
                event_bus.publish("state_change", data={"state": new_state.value})
            except Exception:
                pass

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
        Starts the background speech orchestration state machine loop.
        """
        if self.is_running:
            logger.warning("SpeechManager is already running.")
            return

        self.is_running = True
        self.transition_to(SpeechState.WAKING)
        self.microphone.start_stream()
        self._loop_task = asyncio.create_task(self._run_orchestration_loop())
        logger.info("SpeechManager started background audio loop.")

    async def stop(self) -> None:
        """
        Stops the speech manager, releases microphone stream, cancels active tasks, and halts loop.
        """
        if not self.is_running:
            return

        logger.info("Stopping SpeechManager subsystems and cancelling active tasks...")
        self.is_running = False
        self.transition_to(SpeechState.SHUTDOWN)

        if self._active_speech_task and not self._active_speech_task.done():
            self._active_speech_task.cancel()
            try:
                await self._active_speech_task
            except asyncio.CancelledError:
                pass
            self._active_speech_task = None

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
        Primary asynchronous loop running the formal state machine.
        """
        logger.info("Entering SpeechManager orchestration state loop.")

        # Audio accumulator buffers
        rolling_wake_buffer: List[bytes] = []
        active_speech_buffer: List[bytes] = []

        # Tracking active timers for silence detection
        silence_start_time: Optional[float] = None
        speech_started = False
        speech_start_time: Optional[float] = None
        listening_entry_time: Optional[float] = None

        # Interruption tracking counter
        interruption_consecutive_frames = 0
        recent_activity_count = 0

        while self.is_running:
            try:
                # Read 30ms audio frame from microphone stream
                chunk = await self.microphone.read_chunk()
                is_voice = self.recognizer.is_speech(chunk)

                # =============================================================
                # STATE: WAKING
                # =============================================================
                if self.state == SpeechState.WAKING:
                    rolling_wake_buffer.append(chunk)

                    if is_voice:
                        recent_activity_count = 10
                    elif recent_activity_count > 0:
                        recent_activity_count -= 1

                    if len(rolling_wake_buffer) > 50:
                        rolling_wake_buffer.pop(0)

                    # Transcribe candidates when speech is present in rolling buffer
                    if len(rolling_wake_buffer) >= 33 and recent_activity_count > 0:
                        full_audio = b"".join(rolling_wake_buffer)
                        del rolling_wake_buffer[:10]

                        transcription = await self.recognizer.transcribe_audio(full_audio)
                        logger.info("Wake word candidate text: '%s' (Confidence: %.2f)", transcription.text, transcription.confidence)

                        if self.wakeword.detect_in_text(transcription.text, transcription.confidence):
                            logger.info("Wake word triggered by text '%s'.", transcription.text)
                            self.console.print("[bold yellow]🎙️  [Wake Word] 'Jarvis' detected! Listening...[/bold yellow]")

                            # Single-point queue flush and transition
                            self.microphone.clear_queue()
                            rolling_wake_buffer.clear()
                            active_speech_buffer.clear()
                            recent_activity_count = 0

                            self.transition_to(SpeechState.LISTENING)
                            silence_start_time = None
                            speech_started = False
                            speech_start_time = None
                            listening_entry_time = time.time()

                # =============================================================
                # STATE: LISTENING
                # =============================================================
                elif self.state == SpeechState.LISTENING:
                    active_speech_buffer.append(chunk)

                    if is_voice:
                        if not speech_started:
                            logger.info("Active user speech started.")
                            speech_started = True
                            speech_start_time = time.time()
                        silence_start_time = None
                    else:
                        if speech_started:
                            if silence_start_time is None:
                                silence_start_time = time.time()
                            else:
                                elapsed_silence = time.time() - silence_start_time
                                elapsed_speech = time.time() - speech_start_time if speech_start_time else 0.0

                                # Stop boundary or max command duration reached
                                if elapsed_silence >= self.recognizer.silence_timeout or elapsed_speech >= self.maximum_command_duration:
                                    logger.info("VAD: Stop boundary reached. Silence: %.2fs, Speech: %.2fs", elapsed_silence, elapsed_speech)

                                    if elapsed_speech >= self.recognizer.min_speech_duration:
                                        self.transition_to(SpeechState.TRANSCRIBING)
                                        full_audio_bytes = b"".join(active_speech_buffer)
                                        active_speech_buffer.clear()
                                        speech_started = False

                                        # Process transcription & intelligence pipeline
                                        await self._process_command_pipeline(full_audio_bytes)
                                    else:
                                        logger.info("Captured speech too short (%.2fs < %.2fs). Discarding.", elapsed_speech, self.recognizer.min_speech_duration)
                                        self.transition_to(SpeechState.WAKING)
                                        active_speech_buffer.clear()
                                        speech_started = False
                        else:
                            # Bound pre-speech context buffer (~1s)
                            if len(active_speech_buffer) > 33:
                                active_speech_buffer.pop(0)

                    # Max command duration safety limit
                    if speech_started and speech_start_time and (time.time() - speech_start_time) >= self.maximum_command_duration:
                        logger.info("VAD: Maximum recording duration reached. Terminating recording.")
                        self.transition_to(SpeechState.TRANSCRIBING)
                        full_audio_bytes = b"".join(active_speech_buffer)
                        active_speech_buffer.clear()
                        speech_started = False

                        await self._process_command_pipeline(full_audio_bytes)

                    # Listening idle timeout limit
                    if not speech_started and listening_entry_time and (time.time() - listening_entry_time) >= self.listening_timeout:
                        logger.info("VAD: Listening state idle timeout reached. Returning to WAKING.")
                        self.transition_to(SpeechState.WAKING)
                        active_speech_buffer.clear()
                        speech_started = False

                # =============================================================
                # STATE: SPEAKING (With Interruption Handling)
                # =============================================================
                elif self.state == SpeechState.SPEAKING:
                    if is_voice:
                        interruption_consecutive_frames += 1
                        if interruption_consecutive_frames >= self.interruption_sensitivity:
                            logger.info("User interruption detected (%d speech frames). Interrupting TTS playback...", interruption_consecutive_frames)
                            self.transition_to(SpeechState.INTERRUPTED)

                            # Execute Interruption Sequence
                            self.synthesizer.stop()
                            self.microphone.clear_queue()
                            active_speech_buffer.clear()
                            interruption_consecutive_frames = 0

                            # Immediately capture new user command
                            self.transition_to(SpeechState.LISTENING)
                            silence_start_time = None
                            speech_started = False
                            speech_start_time = None
                            listening_entry_time = time.time()
                    else:
                        interruption_consecutive_frames = 0

                    # Check if speech playback completed
                    if not self.synthesizer.is_speaking and self.state == SpeechState.SPEAKING:
                        self.microphone.clear_queue()
                        self.transition_to(SpeechState.WAKING)

                # =============================================================
                # STATE: ERROR RECOVERY
                # =============================================================
                elif self.state == SpeechState.ERROR:
                    logger.warning("SpeechManager recovering from error state. Resetting queues...")
                    self.microphone.clear_queue()
                    rolling_wake_buffer.clear()
                    active_speech_buffer.clear()
                    await asyncio.sleep(0.1)
                    self.transition_to(SpeechState.WAKING)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Error in SpeechManager execution loop: %s", e)
                self.transition_to(SpeechState.ERROR)

    async def _process_command_pipeline(self, audio_bytes: bytes) -> None:
        """
        Executes TRANSCRIBING -> THINKING -> SPEAKING pipeline sequentially.

        Args:
            audio_bytes: Captured PCM16 mono command audio bytes.
        """
        try:
            # 1. TRANSCRIBING State
            trans_result = await self.recognizer.transcribe_audio(audio_bytes)
            clean_text = trans_result.text.strip()

            if not clean_text:
                logger.info("Transcribed audio yielded empty text. Discarding block.")
                self.transition_to(SpeechState.WAKING)
                return

            try:
                from web.state import event_bus
                event_bus.publish("transcription", data={"text": clean_text})
            except Exception:
                pass

            self.console.print(f"[bold green]User prompt transcribed:[/bold green] [italic]'{clean_text}'[/italic]")

            # 2. THINKING State
            self.transition_to(SpeechState.THINKING)
            response_text = ""
            if self._speech_callback:
                response_text = await self._speech_callback(clean_text)

            if not response_text or not response_text.strip():
                logger.info("Intelligence layer returned empty response.")
                self.transition_to(SpeechState.WAKING)
                return

            # 3. SPEAKING State
            self.transition_to(SpeechState.SPEAKING)
            await self.synthesizer.speak(response_text)

        except Exception as e:
            logger.exception("Error in command pipeline processing: %s", e)
            self.transition_to(SpeechState.ERROR)
