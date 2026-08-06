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
class MicrophoneConfig:
    """Microphone device settings."""
    device: str = "default"
    sample_rate: int = 16000
    channels: int = 1
    use_simulator: bool = False


@dataclass
class VADConfig:
    """Voice Activity Detection settings."""
    sensitivity: int = 3
    silence_timeout: float = 1.5
    min_speech_duration: float = 0.3


@dataclass
class WhisperConfig:
    """Faster Whisper Speech-to-Text settings."""
    model: str = "tiny"
    language: str = "en"
    compute_type: str = "float32"
    use_gpu: bool = False


@dataclass
class WakeWordConfig:
    """Wake Word settings."""
    phrase: str = "jarvis"
    cooldown: float = 2.0
    ignore_accidental_probability: float = 0.1


@dataclass
class PiperConfig:
    """Piper Text-to-Speech settings."""
    voice: str = "en_US-lessac-medium"
    speed: float = 1.0
    piper_path: str = "piper"
    use_simulator: bool = False


@dataclass
class Settings:
    """Global Settings registry for JARVIS."""
    app: AppConfig = field(default_factory=AppConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    speech: SpeechConfig = field(default_factory=SpeechConfig)
    microphone: MicrophoneConfig = field(default_factory=MicrophoneConfig)
    vad: VADConfig = field(default_factory=VADConfig)
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    wakeword: WakeWordConfig = field(default_factory=WakeWordConfig)
    piper: PiperConfig = field(default_factory=PiperConfig)

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
    mic_data: Dict[str, Any] = raw_config.get("microphone", {})
    vad_data: Dict[str, Any] = raw_config.get("vad", {})
    whisper_data: Dict[str, Any] = raw_config.get("whisper", {})
    wakeword_data: Dict[str, Any] = raw_config.get("wakeword", {})
    piper_data: Dict[str, Any] = raw_config.get("piper", {})

    # 5. Environment variable overrides (Upper-case representation)

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

    # Microphone overrides
    mic_device = os.getenv("MICROPHONE_DEVICE", mic_data.get("device", "default"))
    mic_sr_str = os.getenv("MICROPHONE_SAMPLE_RATE", str(mic_data.get("sample_rate", 16000)))
    try:
        mic_sr = int(mic_sr_str)
    except ValueError:
        mic_sr = 16000
    mic_channels_str = os.getenv("MICROPHONE_CHANNELS", str(mic_data.get("channels", 1)))
    try:
        mic_channels = int(mic_channels_str)
    except ValueError:
        mic_channels = 1
    mic_sim_str = os.getenv("MICROPHONE_USE_SIMULATOR", str(mic_data.get("use_simulator", "false")))
    mic_sim = mic_sim_str.lower() in ("true", "1", "yes")

    # VAD overrides
    vad_sens_str = os.getenv("VAD_SENSITIVITY", str(vad_data.get("sensitivity", 3)))
    try:
        vad_sens = int(vad_sens_str)
    except ValueError:
        vad_sens = 3
    vad_timeout_str = os.getenv("VAD_SILENCE_TIMEOUT", str(vad_data.get("silence_timeout", 1.5)))
    try:
        vad_timeout = float(vad_timeout_str)
    except ValueError:
        vad_timeout = 1.5
    vad_min_speech_str = os.getenv("VAD_MIN_SPEECH_DURATION", str(vad_data.get("min_speech_duration", 0.3)))
    try:
        vad_min_speech = float(vad_min_speech_str)
    except ValueError:
        vad_min_speech = 0.3

    # Whisper overrides
    whisper_model = os.getenv("WHISPER_MODEL", whisper_data.get("model", "tiny"))
    whisper_lang = os.getenv("WHISPER_LANGUAGE", whisper_data.get("language", "en"))
    whisper_comp = os.getenv("WHISPER_COMPUTE_TYPE", whisper_data.get("compute_type", "float32"))
    whisper_gpu_str = os.getenv("WHISPER_USE_GPU", str(whisper_data.get("use_gpu", "false")))
    whisper_gpu = whisper_gpu_str.lower() in ("true", "1", "yes")

    # Wake Word overrides
    wakeword_phrase = os.getenv("WAKEWORD_PHRASE", wakeword_data.get("phrase", "jarvis"))
    wakeword_cooldown_str = os.getenv("WAKEWORD_COOLDOWN", str(wakeword_data.get("cooldown", 2.0)))
    try:
        wakeword_cooldown = float(wakeword_cooldown_str)
    except ValueError:
        wakeword_cooldown = 2.0
    wakeword_acc_str = os.getenv("WAKEWORD_IGNORE_ACCIDENTAL_PROBABILITY", str(wakeword_data.get("ignore_accidental_probability", 0.1)))
    try:
        wakeword_acc = float(wakeword_acc_str)
    except ValueError:
        wakeword_acc = 0.1

    # Piper overrides
    piper_voice = os.getenv("PIPER_VOICE", piper_data.get("voice", "en_US-lessac-medium"))
    piper_speed_str = os.getenv("PIPER_SPEED", str(piper_data.get("speed", 1.0)))
    try:
        piper_speed = float(piper_speed_str)
    except ValueError:
        piper_speed = 1.0
    piper_path = os.getenv("PIPER_PATH", piper_data.get("piper_path", "piper"))
    piper_sim_str = os.getenv("PIPER_USE_SIMULATOR", str(piper_data.get("use_simulator", "false")))
    piper_sim = piper_sim_str.lower() in ("true", "1", "yes")

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
        ),
        microphone=MicrophoneConfig(
            device=mic_device,
            sample_rate=mic_sr,
            channels=mic_channels,
            use_simulator=mic_sim
        ),
        vad=VADConfig(
            sensitivity=vad_sens,
            silence_timeout=vad_timeout,
            min_speech_duration=vad_min_speech
        ),
        whisper=WhisperConfig(
            model=whisper_model,
            language=whisper_lang,
            compute_type=whisper_comp,
            use_gpu=whisper_gpu
        ),
        wakeword=WakeWordConfig(
            phrase=wakeword_phrase,
            cooldown=wakeword_cooldown,
            ignore_accidental_probability=wakeword_acc
        ),
        piper=PiperConfig(
            voice=piper_voice,
            speed=piper_speed,
            piper_path=piper_path,
            use_simulator=piper_sim
        )
    )


# Singleton settings instance for global usage
settings: Settings = load_settings()
