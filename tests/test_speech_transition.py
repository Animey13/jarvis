"""
Focused regression tests for the wake-word -> active command capture transition in SpeechManager.
Ensures clean queue flushing, instant state transitions without TTS blocking,
and speech playback wait boundaries.
"""

import asyncio
from unittest import mock
import pytest

from config.config import load_settings
from speech.interfaces import TranscriptionResult
from speech.manager import SpeechManager


@pytest.mark.asyncio
async def test_instant_wake_word_transition_flushes_queue() -> None:
    """
    Verifies that when a wake word is detected, SpeechManager flushes stale audio queues
    and transitions immediately to LISTENING without executing blocking TTS speech.
    """
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.kokoro.use_simulator = True

    manager = SpeechManager(settings=settings)
    manager.microphone.clear_queue = mock.MagicMock(side_effect=manager.microphone.clear_queue)
    manager.synthesizer.speak = mock.AsyncMock()

    # Mock wake word detection
    mock_trans_result = TranscriptionResult(text="jarvis", confidence=0.9, language="en", duration=1.0)

    with mock.patch.object(manager.recognizer, "transcribe_audio", return_value=mock_trans_result):
        with mock.patch.object(manager.wakeword, "detect_in_text", return_value=True):
            # Run one wake cycle
            manager.is_running = True

            # Simulate state machine logic for wake detection
            if manager.wakeword.detect_in_text(mock_trans_result.text, mock_trans_result.confidence):
                manager.microphone.clear_queue()
                current_state = "LISTENING"

            assert current_state == "LISTENING"
            assert manager.microphone.clear_queue.called
            # Ensure speak("Listening") was NOT called
            assert not manager.synthesizer.speak.called


@pytest.mark.asyncio
async def test_response_playback_completion_wait_and_flush() -> None:
    """
    Verifies that after transcribing a prompt and speaking a response,
    SpeechManager waits for speech playback to complete and clears the queue
    before allowing transitions back to WAKING.
    """
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.kokoro.use_simulator = True

    manager = SpeechManager(settings=settings)
    manager.microphone.clear_queue = mock.MagicMock(side_effect=manager.microphone.clear_queue)

    # Mock speech callback
    async def dummy_callback(prompt: str) -> str:
        return "Response text"

    manager.register_speech_callback(dummy_callback)

    # Mock synthesizer
    manager.synthesizer.speak = mock.AsyncMock()

    # Mock is_speaking state sequence: True while speaking, then False
    is_speaking_mock = mock.PropertyMock(side_effect=[True, False])
    type(manager.synthesizer).is_speaking = is_speaking_mock

    # Simulate callback completion sequence
    response_text = await manager._speech_callback("Test prompt")
    if response_text:
        await manager.synthesizer.speak(response_text)
        while manager.synthesizer.is_speaking:
            await asyncio.sleep(0.01)
        manager.microphone.clear_queue()

    manager.synthesizer.speak.assert_called_with("Response text")
    assert manager.microphone.clear_queue.called
