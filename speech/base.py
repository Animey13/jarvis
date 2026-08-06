"""
JARVIS Speech Base Interface Module.

Defines the abstract base classes for Speech-To-Text (STT) and Text-To-Speech (TTS).
"""

from abc import ABC, abstractmethod


class BaseSpeechToText(ABC):
    """
    Abstract Base Class for Speech-To-Text translation.
    Subclasses should integrate with offline (e.g., Whisper) or online STT engines.
    """

    def __init__(self, device_name: str = "default") -> None:
        """
        Initializes the STT driver.

        Args:
            device_name: The name/ID of the audio hardware device to listen on.
        """
        self.device_name: str = device_name

    @abstractmethod
    async def listen(self) -> str:
        """
        Listens to audio from the input device and processes it into text.

        Returns:
            str: The transcribed text.
        """
        pass


class BaseTextToSpeech(ABC):
    """
    Abstract Base Class for Text-To-Speech synthesis.
    Subclasses should integrate with local or cloud TTS speech engines.
    """

    def __init__(self, voice_id: str, rate: int = 150) -> None:
        """
        Initializes the TTS driver.

        Args:
            voice_id: Identifier of the target synthesized voice.
            rate: Speed rate of speaking (words per minute).
        """
        self.voice_id: str = voice_id
        self.rate: int = rate

    @abstractmethod
    async def speak(self, text: str) -> None:
        """
        Synthesizes the provided text into speech audio and plays it.

        Args:
            text: The text to convert and speak.
        """
        pass
