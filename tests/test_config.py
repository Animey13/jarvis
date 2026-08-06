"""
Unit tests for the JARVIS Configuration System.
"""

import os
from pathlib import Path
from unittest import mock
from config.config import load_settings


def test_default_config_loading() -> None:
    """Verifies that settings load with correct defaults when no overrides are set."""
    settings = load_settings()
    assert settings.app.name == "JARVIS"
    assert settings.logging.level in ("INFO", "DEBUG", "WARNING", "ERROR")
    assert settings.llm.provider == "ollama"


def test_environment_variable_overrides() -> None:
    """Verifies that environment variables successfully override YAML configurations."""
    with mock.patch.dict(os.environ, {
        "APP_NAME": "TEST-JARVIS",
        "APP_ENV": "testing",
        "LOG_LEVEL": "DEBUG",
        "LLM_MODEL": "llama2:7b",
        "LLM_TIMEOUT": "15.5",
        "SPEECH_INPUT_DEVICE": "mic1"
    }):
        settings = load_settings()
        assert settings.app.name == "TEST-JARVIS"
        assert settings.app.env == "testing"
        assert settings.logging.level == "DEBUG"
        assert settings.llm.model == "llama2:7b"
        assert settings.llm.timeout == 15.5
        assert settings.speech.input_device == "mic1"


def test_get_log_file_path() -> None:
    """Verifies that the absolute path to the log file is generated correctly."""
    settings = load_settings()
    path = settings.get_log_file_path()
    assert isinstance(path, Path)
    assert path.name == "jarvis.log"
