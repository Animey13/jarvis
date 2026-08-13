"""
Unit tests for the JARVIS Core Assistant class.
"""

import asyncio
from unittest import mock
import pytest
from app.assistant import JarvisAssistant
from config.config import load_settings


def test_assistant_initialization() -> None:
    """Verifies assistant properties are initialized correctly from configuration."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    assistant = JarvisAssistant(settings=settings)
    assert assistant.settings == settings
    assert not assistant.is_running


def test_display_banner() -> None:
    """Ensures display_banner can run without causing exceptions."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    assistant = JarvisAssistant(settings=settings)

    with mock.patch.object(assistant.console, "print") as mock_print:
        assistant.display_banner()
        assert mock_print.called


@pytest.mark.asyncio
async def test_assistant_graceful_stop() -> None:
    """Verifies that calling stop() is graceful and works as expected."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    assistant = JarvisAssistant(settings=settings)

    assistant.is_running = True
    with mock.patch.object(assistant.console, "print") as mock_print:
        await assistant.stop()
        assert not assistant.is_running
        assert mock_print.called


@pytest.mark.asyncio
async def test_run_loop_with_immediate_exit() -> None:
    """Simulates the interactive loop receiving 'exit' and exiting gracefully."""
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    assistant = JarvisAssistant(settings=settings)

    assistant.is_running = True
    assistant._shutdown_event = asyncio.Event()

    with mock.patch("asyncio.get_running_loop") as mock_get_loop:
        mock_loop = mock.MagicMock()

        fut = asyncio.Future()
        fut.set_result("exit")

        mock_loop.run_in_executor.return_value = fut
        mock_get_loop.return_value = mock_loop

        await assistant._run_loop()

        assert assistant._shutdown_event.is_set()


@pytest.mark.asyncio
async def test_process_text_input_with_tool_calling() -> None:
    """
    Verifies that process_text_input detects a tool call, executes it, and
    provides a final summarized answer from the LLM.
    """
    settings = load_settings()
    settings.microphone.use_simulator = True
    settings.piper.use_simulator = True
    assistant = JarvisAssistant(settings=settings)

    # Mock OllamaClient.generate:
    # 1. First call outputs a tool tag.
    # 2. Second call outputs a friendly summarized string using the tool data.
    first_response = "[TOOL: get_current_datetime]"
    second_response = "The current system time is Sunday, April 13, 2025, 03:00 PM."

    with mock.patch.object(assistant.llm_client, "generate") as mock_generate:
        mock_generate.side_effect = [first_response, second_response]

        # Execute text processing
        result = await assistant.process_text_input("What time is it?")

        # Check call count and result
        assert mock_generate.call_count == 2
        assert result == second_response

        # Check that the first query includes tool descriptions
        first_call_args = mock_generate.call_args_list[0]
        assert "get_current_datetime" in first_call_args[1]["system_prompt"]

        # Check that the second query includes the raw tool result
        second_call_args = mock_generate.call_args_list[1]
        assert "friendly_text" in second_call_args[0][0]
        assert "User original query: What time is it?" in second_call_args[0][0]
