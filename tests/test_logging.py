"""
Unit tests for the JARVIS Logging Configuration.
"""

import logging
from pathlib import Path
from app.logging_config import configure_logging


def test_configure_logging(tmp_path: Path) -> None:
    """Verifies that the logging configuration registers appropriate handlers and directories."""
    log_file = tmp_path / "test_logs" / "test_jarvis.log"

    # Configure logging using our custom temp path
    configure_logging(
        log_level="DEBUG",
        log_file=log_file,
        console_output=True
    )

    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG

    # Check that file handler was created and is writing to the correct path
    file_handler_found = False
    console_handler_found = False

    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler):
            assert Path(handler.baseFilename).resolve() == log_file.resolve()
            file_handler_found = True
        else:
            console_handler_found = True

    assert file_handler_found
    assert console_handler_found

    # Test that logging actually writes to the file
    test_logger = logging.getLogger("test_logger")
    test_logger.debug("Test output to log file.")

    for handler in root_logger.handlers:
        handler.flush()

    assert log_file.exists()
    content = log_file.read_text(encoding="utf-8")
    assert "Test output to log file." in content
