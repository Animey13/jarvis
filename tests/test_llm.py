"""
Unit tests for the JARVIS LLM subsystem (Ollama Client).
"""

import json
from typing import Any
from unittest import mock
import pytest
import httpx

from config.config import load_settings
from llm.ollama import OllamaClient


def test_ollama_client_initialization() -> None:
    """Verifies that the OllamaClient initializes with correct parameters."""
    client = OllamaClient(model_name="test-llama", api_base="http://testbase:11434", timeout=15.0)
    assert client.model_name == "test-llama"
    assert client.api_base == "http://testbase:11434"
    assert client.timeout == 15.0


@pytest.mark.asyncio
async def test_ollama_generate_success() -> None:
    """Tests successful synchronous prompt completion generation from Ollama."""
    client = OllamaClient(model_name="test-llama", api_base="http://localhost:11434")

    mock_request = httpx.Request("POST", "http://localhost:11434/api/generate")
    mock_response = httpx.Response(
        status_code=200,
        json={"response": "Hello, I am JARVIS."},
        request=mock_request
    )

    # Mock httpx.AsyncClient.post
    with mock.patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
        result = await client.generate("How are you?")
        assert result == "Hello, I am JARVIS."

        # Verify post payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "http://localhost:11434/api/generate"
        assert kwargs["json"]["model"] == "test-llama"
        assert kwargs["json"]["prompt"] == "How are you?"
        assert kwargs["json"]["stream"] is False


@pytest.mark.asyncio
async def test_ollama_generate_stream() -> None:
    """Tests successful streaming prompt completion generation from Ollama."""
    client = OllamaClient(model_name="test-llama", api_base="http://localhost:11434")

    # Simple line-delimited json stream chunks
    chunks = [
        b'{"response": "Hello", "done": false}\n',
        b'{"response": " world", "done": false}\n',
        b'{"response": "!", "done": true}\n'
    ]

    # Helper async generator for mock stream iter_lines
    async def mock_iter_lines(*args: Any, **kwargs: Any):
        for chunk in chunks:
            yield chunk.decode("utf-8")

    mock_stream = mock.MagicMock()
    mock_stream.aiter_lines = mock_iter_lines
    mock_stream.raise_for_status = mock.MagicMock()

    # Mock httpx.AsyncClient.stream context manager
    with mock.patch("httpx.AsyncClient.stream", return_value=mock.MagicMock(__aenter__=mock.AsyncMock(return_value=mock_stream))):
        results = []
        async for chunk in client.generate_stream("Hello"):
            results.append(chunk)

        assert "".join(results) == "Hello world!"


@pytest.mark.asyncio
async def test_ollama_generate_connection_failure() -> None:
    """Verifies that OllamaClient raises ConnectionError gracefully when the server is offline."""
    client = OllamaClient(model_name="test-llama", api_base="http://offline-ollama:11434")

    with mock.patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Connection refused")):
        with pytest.raises(ConnectionError) as exc_info:
            await client.generate("Hello")
        assert "Could not connect to local Ollama server" in str(exc_info.value)
