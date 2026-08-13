"""
JARVIS Local JSON Memory Module.

Implements the BaseMemory interface to persistently store and retrieve conversational
history inside a local JSON file on disk, enabling contextual chat.
"""

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from memory.base import BaseMemory

logger = logging.getLogger(__name__)


class LocalJSONMemory(BaseMemory):
    """
    Offline-first persistent memory driver that stores conversational logs in a local JSON file.
    """

    def __init__(self, file_path: str = "logs/memory.json") -> None:
        """
        Initializes the LocalJSONMemory driver.

        Args:
            file_path: Relative or absolute path where the memory JSON file is saved.
        """
        from config.config import BASE_DIR
        self.file_path = Path(file_path)
        if not self.file_path.is_absolute():
            self.file_path = BASE_DIR / self.file_path

        # Ensure target directory exists
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create memory folder path: %s", e)

        logger.info("LocalJSONMemory initialized. Storage file: '%s'", self.file_path)

    def _read_memory_file(self) -> List[Dict[str, Any]]:
        """Reads and parses raw records from the local JSON file safely."""
        if not self.file_path.exists():
            return []

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return []
                data = json.loads(content)
                if isinstance(data, list):
                    return data
        except Exception as e:
            logger.error("Failed to read/decode memory JSON file: %s. Starting fresh.", e)
        return []

    def _write_memory_file(self, records: List[Dict[str, Any]]) -> None:
        """Writes records back safely to the local JSON file."""
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to write to memory JSON file: %s", e)

    async def store(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Stores an item or conversation turn in persistent local memory.

        Args:
            content: The text content of the conversation turn.
            metadata: Optional dictionary properties (e.g. role: user/assistant, timestamps).
        """
        if metadata is None:
            metadata = {}

        # Ensure standard keys are registered
        if "timestamp" not in metadata:
            metadata["timestamp"] = time.time()

        record = {
            "content": content,
            "metadata": metadata
        }

        # Read, append, and save
        records = self._read_memory_file()
        records.append(record)
        self._write_memory_file(records)
        logger.debug("LocalJSONMemory: stored record successfully (Length: %d chars).", len(content))

    async def retrieve(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent conversation records matching a simple text query,
        or simply gets the last N records if the query is empty.

        Args:
            query: Simple query string to filter content, or empty for last N records.
            limit: Maximum number of records to retrieve.

        Returns:
            List[Dict[str, Any]]: List of matching records containing content and metadata.
        """
        records = self._read_memory_file()

        # Scenario A: empty query, retrieve the last N conversational turns
        if not query.strip():
            results = records[-limit:] if len(records) >= limit else records
            logger.debug("LocalJSONMemory: retrieved last %d records.", len(results))
            return results

        # Scenario B: basic substring search over records
        matching_records = []
        clean_query = query.strip().lower()
        for record in records:
            if clean_query in record.get("content", "").lower():
                matching_records.append(record)

        results = matching_records[-limit:] if len(matching_records) >= limit else matching_records
        logger.debug("LocalJSONMemory: retrieved %d records matching query '%s'.", len(results), query)
        return results

    async def clear(self) -> None:
        """
        Clears/resets all persistent conversational logs from the JSON store.
        """
        self._write_memory_file([])
        logger.info("LocalJSONMemory successfully cleared.")
