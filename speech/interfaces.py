"""
JARVIS Speech Interface Definitions.

Provides abstract base interfaces for the Microphone Input, Speech Recognizer,
and Speech Synthesizer subsystems, inheriting from existing Phase 1 abstractions.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from speech.base import BaseSpeechToText, BaseTextToSpeech


@dataclass
class TranscriptionResult:
    """
    Structure representing a speech transcription result.
    """
    text: str
    confidence: float
    language: str
    duration: float
    segments: List[Dict[str, Any]] = field(default_factory=list)


class AudioInput(ABC):
    """
    Abstract Base Class for managing microphone and audio streaming hardware.
    """

    @abstractmethod
    def start_stream(self) -> None:
        """
        Starts the audio input capture stream.
        """
        pass

    @abstractmethod
    def stop_stream(self) -> None:
        """
        Stops the audio input capture stream.
        """
        pass

    @abstractmethod
    async def read_chunk(self) -> bytes:
        """
        Reads an audio chunk from the input stream.

        Returns:
            bytes: Raw PCM audio frame data.
        """
        pass

    @abstractmethod
    def get_devices(self) -> List[Dict[str, Any]]:
        """
        Queries and returns a list of available audio input devices.

        Returns:
            List[Dict[str, Any]]: List of device dictionaries containing name, sample rate, etc.
        """
        pass


class SpeechRecognizer(BaseSpeechToText, ABC):
    """
    Abstract Base Class for Speech-to-Text (STT) Engines.
    Extends Phase 1 BaseSpeechToText to preserve backward compatibility.
    """

    def __init__(self, model_name: str, language: str = "en", device_name: str = "default") -> None:
        """
        Initializes the Speech Recognizer.

        Args:
            model_name: The speech model configuration name/size.
            language: Target ISO code of spoken language (e.g. 'en').
            device_name: Name of audio input device.
        """
        super().__init__(device_name=device_name)
        self.model_name: str = model_name
        self.language: str = language

    @abstractmethod
    async def transcribe_audio(self, audio_data: bytes) -> TranscriptionResult:
        """
        Transcribes a block of raw audio data into structured text.

        Args:
            audio_data: The raw PCM audio bytes to transcribe.

        Returns:
            TranscriptionResult: Structured details of transcription.
        """
        pass


class SpeechSynthesizer(BaseTextToSpeech, ABC):
    """
    Abstract Base Class for Text-to-Speech (TTS) Engines.
    Extends Phase 1 BaseTextToSpeech to preserve backward compatibility.
    """

    def __init__(self, voice_id: str, rate: int = 150) -> None:
        """
        Initializes the Speech Synthesizer.

        Args:
            voice_id: Name of target speaking voice.
            rate: General speaking rate (speed/words-per-minute).
        """
        super().__init__(voice_id=voice_id, rate=rate)

    @abstractmethod
    def stop(self) -> None:
        """
        Interrupts and immediately stops any ongoing speech playback.
        """
        pass

    @abstractmethod
    async def speak_queued(self, text: str) -> None:
        """
        Queues the provided text for speech, playing it in FIFO order.

        Args:
            text: Text block to synthesize and queue.
        """
        pass
