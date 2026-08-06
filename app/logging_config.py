"""
JARVIS Logging Configuration Module.

Configures application-wide logging using Rich for beautiful console output
and rotating file handlers for persistent storage.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Union

from rich.logging import RichHandler


def configure_logging(
    log_level: str = "INFO",
    log_file: Union[str, Path] = "logs/jarvis.log",
    console_output: bool = True
) -> None:
    """
    Configures the global logging system with console and rotating file handlers.

    Args:
        log_level: The logging severity level (e.g., DEBUG, INFO, WARNING, ERROR).
        log_file: Path to the log file.
        console_output: Whether to enable logging to the console via Rich.
    """
    # 1. Map string log levels to logging constants
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    # 2. Reset existing handlers on root logger to avoid duplicates
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    root_logger.setLevel(numeric_level)

    # 3. Create handlers list
    handlers: list[logging.Handler] = []

    # Console Handler (Rich)
    if console_output:
        rich_handler = RichHandler(
            level=numeric_level,
            show_path=True,
            show_time=True,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
        )
        # Format for console can be minimal since Rich supplies time and levels nicely
        rich_formatter = logging.Formatter("%(message)s")
        rich_handler.setFormatter(rich_formatter)
        handlers.append(rich_handler)

    # File Handler (Rotating)
    file_path = Path(log_file)
    if not file_path.is_absolute():
        from config.config import BASE_DIR
        file_path = BASE_DIR / file_path

    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # 5MB max file size, keeping up to 5 backups
        file_handler = RotatingFileHandler(
            filename=file_path,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )
        file_handler.setLevel(numeric_level)
        file_formatter = logging.Formatter(
            "[%(asctime)s] [%(levelname)-8s] [%(name)s:%(funcName)s:%(lineno)d] - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    except OSError as e:
        print(f"CRITICAL: Failed to initialize file logger at {file_path}: {e}")

    # 4. Configure root logger with the handlers
    for handler in handlers:
        root_logger.addHandler(handler)

    # Log successful initialization
    logger = logging.getLogger(__name__)
    logger.info("Logging initialized. Level: %s, Console: %s, File: %s", log_level, console_output, file_path)
