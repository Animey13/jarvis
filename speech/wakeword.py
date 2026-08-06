"""
JARVIS Wake Word Detection Module.

Defines a modular WakeWordEngine supporting offline keyword detection (spotting).
Can be easily swapped for Porcupine or OpenWakeWord in later phases.
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class WakeWordEngine:
    """
    Modular Wake Word Engine for detecting activation phrases in audio streams.
    Swappable with alternative engines (e.g., Porcupine, OpenWakeWord).
    """

    def __init__(
        self,
        phrase: str = "jarvis",
        cooldown: float = 2.0,
        ignore_accidental_probability: float = 0.1
    ) -> None:
        """
        Initializes the WakeWordEngine.

        Args:
            phrase: The wake word text phrase to search for (case-insensitive).
            cooldown: Time window in seconds during which further activations are suppressed.
            ignore_accidental_probability: Threshold to avoid false-positive triggers.
        """
        self.phrase: str = phrase.strip().lower()
        self.cooldown: float = cooldown
        self.ignore_accidental_probability: float = ignore_accidental_probability

        self._last_activation_time: float = 0.0

        logger.info(
            "WakeWordEngine initialized (Phrase: '%s', Cooldown: %.1fs, Accidental Threshold: %.2f)",
            self.phrase, self.cooldown, self.ignore_accidental_probability
        )

    def detect_in_text(self, text: str, confidence: float = 1.0) -> bool:
        """
        Scans a transcribed text block for the presence of the wake phrase.
        Includes cooldown gating and accidental activation rejection.

        Args:
            text: Transcribed text string.
            confidence: Confidence score of the transcription.

        Returns:
            bool: True if a valid wake trigger is detected, False otherwise.
        """
        clean_text = text.strip().lower()
        if self.phrase not in clean_text:
            return False

        # 1. Gating check: Cooldown
        now = time.time()
        elapsed = now - self._last_activation_time
        if elapsed < self.cooldown:
            logger.debug(
                "Wake phrase '%s' detected, but ignored due to cooldown (%.1fs remaining).",
                self.phrase, self.cooldown - elapsed
            )
            return False

        # 2. Gating check: Accidental activation limit
        if confidence < self.ignore_accidental_probability:
            logger.warning(
                "Accidental activation ignored: '%s' detected with low confidence (%.2f < %.2f).",
                text, confidence, self.ignore_accidental_probability
            )
            return False

        # Activate
        self._last_activation_time = now
        logger.info("Wake word '%s' successfully detected in text: '%s' (Confidence: %.2f)", self.phrase, text, confidence)
        return True
