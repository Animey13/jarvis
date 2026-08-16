"""
Unit tests for the JARVIS Core Intelligence Layer (JarvisCore).
Tests normal LLM responses, empty inputs, LLM timeouts, network failures,
context tracking, and context bounding limits.
"""

import asyncio
from unittest import mock
import pytest

from app.core import JarvisCore, DEFAULT_FALLBACK_RESPONSE
from config.config import load_settings


@pytest.mark.asyncio
async def test_normal_llm_response() -> None:
    """
    Verifies that JarvisCore processes a normal user text query,
    queries the LLM client, updates history, and returns the response.
    """
    settings = load_settings()
    mock_llm = mock.AsyncMock()
    mock_llm.model_name = "llama3:8b"
    mock_llm.api_base = "http://localhost:11434"
    mock_llm.timeout = 30.0
    mock_llm.generate.return_value = "Hello! I am JARVIS, your assistant."

    core = JarvisCore(settings=settings, llm_client=mock_llm)

    response = await core.respond("Hello JARVIS")

    assert response == "Hello! I am JARVIS, your assistant."
    assert len(core.history) == 2
    assert core.history[0].role == "user"
    assert core.history[0].content == "Hello JARVIS"
    assert core.history[1].role == "assistant"
    assert core.history[1].content == "Hello! I am JARVIS, your assistant."


@pytest.mark.asyncio
async def test_empty_input_handling() -> None:
    """
    Verifies that empty or whitespace-only inputs return a polite prompt
    without invoking the LLM client.
    """
    settings = load_settings()
    mock_llm = mock.AsyncMock()

    core = JarvisCore(settings=settings, llm_client=mock_llm)

    response = await core.respond("   ")

    assert "didn't hear anything" in response
    assert not mock_llm.generate.called
    assert len(core.history) == 0


@pytest.mark.asyncio
async def test_llm_timeout_fallback() -> None:
    """
    Verifies that when the LLM client raises asyncio.TimeoutError or ConnectionError,
    JarvisCore catches the failure gracefully and returns the short spoken fallback response.
    """
    settings = load_settings()
    mock_llm = mock.AsyncMock()
    mock_llm.model_name = "llama3:8b"
    mock_llm.api_base = "http://localhost:11434"
    mock_llm.timeout = 5.0
    mock_llm.generate.side_effect = TimeoutError("LLM Request Timed Out")

    core = JarvisCore(settings=settings, llm_client=mock_llm)

    response = await core.respond("What is the weather?")

    assert response == DEFAULT_FALLBACK_RESPONSE
    # History should not store failed turns
    assert len(core.history) == 0


@pytest.mark.asyncio
async def test_llm_failure_handling() -> None:
    """
    Verifies that network or HTTP exceptions from the LLM client return the fallback message without crashing.
    """
    settings = load_settings()
    mock_llm = mock.AsyncMock()
    mock_llm.model_name = "llama3:8b"
    mock_llm.api_base = "http://localhost:11434"
    mock_llm.timeout = 30.0
    mock_llm.generate.side_effect = RuntimeError("500 Internal Server Error")

    core = JarvisCore(settings=settings, llm_client=mock_llm)

    response = await core.respond("Status report")

    assert response == DEFAULT_FALLBACK_RESPONSE


@pytest.mark.asyncio
async def test_empty_llm_response_handling() -> None:
    """
    Verifies that if the LLM returns an empty string or whitespace,
    JarvisCore returns the fallback response.
    """
    settings = load_settings()
    mock_llm = mock.AsyncMock()
    mock_llm.model_name = "llama3:8b"
    mock_llm.api_base = "http://localhost:11434"
    mock_llm.timeout = 30.0
    mock_llm.generate.return_value = "   "

    core = JarvisCore(settings=settings, llm_client=mock_llm)

    response = await core.respond("Tell me a story")

    assert response == DEFAULT_FALLBACK_RESPONSE


@pytest.mark.asyncio
async def test_context_handling_and_limits() -> None:
    """
    Verifies that conversation turns are formatted into subsequent prompts,
    and that memory history does not exceed max_context_length.
    """
    settings = load_settings()
    mock_llm = mock.AsyncMock()
    mock_llm.model_name = "llama3:8b"
    mock_llm.api_base = "http://localhost:11434"
    mock_llm.timeout = 30.0
    mock_llm.generate.return_value = "Ack"

    # Set small max_context_length = 4 (2 user/assistant pairs)
    core = JarvisCore(settings=settings, llm_client=mock_llm, max_context_length=4)

    await core.respond("Turn 1")
    await core.respond("Turn 2")
    await core.respond("Turn 3")

    # History size should be capped at max_context_length=4
    assert len(core.history) == 4
    assert core.history[0].content == "Turn 2"
    assert core.history[1].content == "Ack"
    assert core.history[2].content == "Turn 3"
    assert core.history[3].content == "Ack"

    # Verify that the generated prompt includes recent history
    prompt = core.build_prompt("Turn 4")
    assert "Recent conversation history:" in prompt
    assert "USER: Turn 2" in prompt
    assert "USER: Turn 4" in prompt
