"""
JARVIS Speech Subpackage.

This package manages speech-to-text (STT) and text-to-speech (TTS)
modules for JARVIS, enabling audio input and output interfaces.
"""

from speech.interfaces import TranscriptionResult
from speech.microphone import MicrophoneManager
from speech.recognizer import FasterWhisperRecognizer
from speech.synthesizer import PiperSynthesizer
from speech.wakeword import WakeWordEngine
from speech.manager import SpeechManager

__all__ = [
    "TranscriptionResult",
    "MicrophoneManager",
    "FasterWhisperRecognizer",
    "PiperSynthesizer",
    "WakeWordEngine",
    "SpeechManager",
]
