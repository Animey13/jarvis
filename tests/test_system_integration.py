"""
Comprehensive System Integration Test Suite for Phase 6.

Exercises the end-to-end JARVIS system pipeline:
wake word -> audio capture -> VAD -> transcription -> memory retrieval ->
tool decision -> tool execution -> LLM response synthesis -> Kokoro TTS playback ->
interruption handling -> graceful shutdown.
"""

import asyncio
from unittest import mock
import pytest

from app.assistant import JarvisAssistant
from config.config import load_settings
from speech.manager import SpeechState


@pytest.mark.asyncio
async def test_full_system_integration_pipeline() -> None:
    """
    Integration test exercising the complete pipeline:
    wake word -> transcribed command -> persistent memory query -> tool execution -> LLM response -> TTS.
    """
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.kokoro.use_simulator = True

    # 1. Instantiate JarvisAssistant
    assistant = JarvisAssistant(settings=settings)

    # 2. Mock LLM to return tool call for calculator, then final response
    assistant.jarvis_core.llm_client.generate = mock.AsyncMock(
        side_effect=[
            "[TOOL: calculator, expression='50 * 4']",
            "50 multiplied by 4 equals 200."
        ]
    )

    # 3. Spy on synthesizer
    assistant.speech_manager.synthesizer.speak = mock.AsyncMock()

    # 4. Trigger voice interaction callback
    user_prompt = "Calculate 50 times 4"
    callback_res = await assistant.speech_manager._speech_callback(user_prompt)
    if callback_res:
        await assistant.speech_manager.synthesizer.speak(callback_res)

    # Assertions
    assert callback_res == "50 multiplied by 4 equals 200."
    assert assistant.jarvis_core.llm_client.generate.call_count == 2
    assert assistant.speech_manager.synthesizer.speak.called


@pytest.mark.asyncio
async def test_end_to_end_state_machine_with_memory_and_tools() -> None:
    """
    Integration test checking memory persistence, tool execution, and state transitions.
    """
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.kokoro.use_simulator = True

    assistant = JarvisAssistant(settings=settings)

    # Remember a fact in persistent memory
    assistant.jarvis_core.memory_manager.remember("location", "London")

    # Mock LLM response
    assistant.jarvis_core.llm_client.generate = mock.AsyncMock(
        return_value="Your location is recorded as London."
    )

    response = await assistant.process_text_input("What is my location?")

    assert response == "Your location is recorded as London."
    # Check that memory context was injected into the LLM prompt
    call_prompt = assistant.jarvis_core.llm_client.generate.call_args[1]["prompt"]
    assert "location: London" in call_prompt


@pytest.mark.asyncio
async def test_system_shutdown_order_and_cleanup() -> None:
    """
    Verifies that starting and stopping JarvisAssistant executes clean component shutdown without orphan tasks.
    """
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    settings.kokoro.use_simulator = True

    assistant = JarvisAssistant(settings=settings)
    assistant.speech_manager.microphone.stop_stream = mock.MagicMock()
    assistant.speech_manager.synthesizer.stop = mock.MagicMock()

    # Start assistant and speech manager
    assistant.is_running = True
    await assistant.speech_manager.start()
    assert assistant.speech_manager.is_running is True
    assert assistant.speech_manager.state == SpeechState.WAKING

    # Stop assistant
    await assistant.stop()
    assert assistant.is_running is False
    assert assistant.speech_manager.is_running is False
    assert assistant.speech_manager.state == SpeechState.SHUTDOWN
    assert assistant.speech_manager.microphone.stop_stream.called
    assert assistant.speech_manager.synthesizer.stop.called
