"""
JARVIS Configuration Management Module.

This module loads configuration settings from a YAML file and overrides them
using environment variables from .env files or the shell environment.
"""

import os
from dataclasses import dataclass, field
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import yaml

# Initialize basic logger for config bootstrap if needed,
# though we will configure main logging later.
logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_PATH = BASE_DIR / "config" / "settings.yaml"


@dataclass
class AppConfig:
    """Core application settings."""
    name: str = "JARVIS"
    env: str = "production"
    debug: bool = False


@dataclass
class LoggingConfig:
    """Logging settings."""
    level: str = "INFO"
    file_path: str = "logs/jarvis.log"
    console_output: bool = True


@dataclass
class LLMConfig:
    """Language Model settings."""
    provider: str = "ollama"
    model: str = "llama3:8b"
    api_base: str = "http://localhost:11434"
    timeout: float = 30.0


@dataclass
class SpeechConfig:
    """Speech and Audio settings."""
    input_device: str = "default"
    tts_provider: str = "local"
    voice_id: str = "en-US-Wavenet-D"


@dataclass
class Settings:
    """Global Settings registry for JARVIS."""
    app: AppConfig = field(default_factory=AppConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    speech: SpeechConfig = field(default_factory=SpeechConfig)

    def get_log_file_path(self) -> Path:
        """
        Returns the absolute path to the log file, ensuring directories exist.

        Returns:
            Path: The absolute path of the log file.
        """
        path = Path(self.logging.file_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        # Ensure directory exists
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Fallback to current working directory if logs directory cannot be created
            fallback_path = BASE_DIR / "jarvis.log"
            print(f"Warning: Failed to create directories for {path}: {e}. Falling back to {fallback_path}")
            return fallback_path
        return path


def load_settings(settings_path: Optional[Path] = None) -> Settings:
    """
    Loads configuration settings by merging defaults, settings.yaml, and environment variables.

    Args:
        settings_path: Optional path to settings.yaml. Defaults to ROOT/config/settings.yaml.

    Returns:
        Settings: An instance of Settings populated with merged values.
    """
    # 1. Load environment variables from .env file
    load_dotenv(dotenv_path=BASE_DIR / ".env")

    # 2. Set default path if not provided
    if settings_path is None:
        settings_path = DEFAULT_SETTINGS_PATH

    raw_config: Dict[str, Any] = {}

    # 3. Read settings.yaml if it exists
    if settings_path.exists():
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    raw_config = loaded
        except Exception as e:
            print(f"Warning: Failed to load settings from {settings_path}: {e}. Using defaults.")
    else:
        print(f"Warning: Settings file not found at {settings_path}. Using defaults.")

    # 4. Extract sections with defaults
    app_data: Dict[str, Any] = raw_config.get("app", {})
    logging_data: Dict[str, Any] = raw_config.get("logging", {})
    llm_data: Dict[str, Any] = raw_config.get("llm", {})
    speech_data: Dict[str, Any] = raw_config.get("speech", {})

    # 5. Environment variable overrides (Upper-case and dot-separated or underscore representation)

    # App overrides
    app_env = os.getenv("APP_ENV", app_data.get("env", "development"))
    app_debug_str = os.getenv("APP_DEBUG", str(app_data.get("debug", "true")))
    app_debug = app_debug_str.lower() in ("true", "1", "yes")
    app_name = os.getenv("APP_NAME", app_data.get("name", "JARVIS"))

    # Logging overrides
    log_level = os.getenv("LOG_LEVEL", logging_data.get("level", "INFO"))
    log_file_path = os.getenv("LOG_FILE_PATH", logging_data.get("file_path", "logs/jarvis.log"))
    console_output_str = os.getenv("LOG_CONSOLE_OUTPUT", str(logging_data.get("console_output", "true")))
    console_output = console_output_str.lower() in ("true", "1", "yes")

    # LLM overrides
    llm_provider = os.getenv("LLM_PROVIDER", llm_data.get("provider", "ollama"))
    llm_model = os.getenv("LLM_MODEL", llm_data.get("model", "llama3:8b"))
    llm_api_base = os.getenv("LLM_API_BASE", llm_data.get("api_base", "http://localhost:11434"))
    llm_timeout_str = os.getenv("LLM_TIMEOUT", str(llm_data.get("timeout", 30.0)))
    try:
        llm_timeout = float(llm_timeout_str)
    except ValueError:
        llm_timeout = 30.0

    # Speech overrides
    speech_input = os.getenv("SPEECH_INPUT_DEVICE", speech_data.get("input_device", "default"))
    speech_tts = os.getenv("SPEECH_TTS_PROVIDER", speech_data.get("tts_provider", "local"))
    speech_voice = os.getenv("SPEECH_VOICE_ID", speech_data.get("voice_id", "en-US-Wavenet-D"))

    # 6. Instantiate settings object
    return Settings(
        app=AppConfig(
            name=app_name,
            env=app_env,
            debug=app_debug
        ),
        logging=LoggingConfig(
            level=log_level,
            file_path=log_file_path,
            console_output=console_output
        ),
        llm=LLMConfig(
            provider=llm_provider,
            model=llm_model,
            api_base=llm_api_base,
            timeout=llm_timeout
        ),
        speech=SpeechConfig(
            input_device=speech_input,
            tts_provider=speech_tts,
            voice_id=speech_voice
        )
    )


# Singleton settings instance for global usage
settings: Settings = load_settings()
