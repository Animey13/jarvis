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
