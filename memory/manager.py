"""
JARVIS Memory Manager Module.

Provides a unified MemoryManager coordinating Short-Term Memory (bounded in-memory context)
and Persistent Memory (structured, intentional key-value fact store persisted to disk as JSON).
"""

import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Coordinates Short-Term (in-session) and Persistent (disk-backed JSON) memory stores.
    """

    def __init__(
        self,
        file_path: str = "logs/persistent_memory.json",
        max_short_term_turns: int = 10
    ) -> None:
        """
        Initializes the MemoryManager.

        Args:
            file_path: Relative or absolute path where persistent memories are stored.
            max_short_term_turns: Maximum number of recent conversation turns kept in short-term memory.
        """
        from config.config import BASE_DIR

        self.file_path = Path(file_path)
        if not self.file_path.is_absolute():
            self.file_path = BASE_DIR / self.file_path

        self.max_short_term_turns = max_short_term_turns
        self.short_term_history: List[Dict[str, str]] = []

        # Ensure directory exists
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error("Failed to create persistent memory directory: %s", e)

        logger.info("MemoryManager initialized. Storage path: '%s'", self.file_path)

    # -------------------------------------------------------------------------
    # PERSISTENT MEMORY OPERATIONS
    # -------------------------------------------------------------------------

    def _read_persistent_file(self) -> Dict[str, Dict[str, Any]]:
        """
        Safely reads persistent memories from disk.
        If file is missing or corrupted, handles failure safely without crashing.
        """
        if not self.file_path.exists():
            return {}

        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if not content:
                    return {}
                data = json.loads(content)
                if isinstance(data, dict):
                    return data
                else:
                    logger.warning("Persistent memory file structure invalid (not a dict). Starting fresh.")
                    return {}
        except (json.JSONDecodeError, OSError, Exception) as e:
            logger.error("Corrupted or unreadable persistent memory file at '%s': %s", self.file_path, e)
            self._backup_corrupted_file()
            return {}

    def _write_persistent_file(self, data: Dict[str, Dict[str, Any]]) -> None:
        """
        Safely writes memory dictionary back to disk.
        """
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error("Failed to write to persistent memory file: %s", e)

    def _backup_corrupted_file(self) -> None:
        """
        Backs up a corrupted persistent memory file to prevent data loss while resetting active memory.
        """
        try:
            if self.file_path.exists():
                backup_path = self.file_path.with_name(f"{self.file_path.name}.corrupted.{int(time.time())}")
                self.file_path.rename(backup_path)
                logger.warning("Renamed corrupted persistent memory file to '%s'", backup_path)
        except Exception as e:
            logger.error("Failed to rename corrupted persistent memory file: %s", e)

    def remember(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Stores an intentional fact, preference, or context item in persistent memory.

        Args:
            key: Unique key identifier for the fact (e.g. 'user_name').
            value: The fact/preference value (e.g. 'Alex').
            metadata: Optional additional metadata dict.

        Returns:
            Dict[str, Any]: The stored memory record.
        """
        if not key or not str(key).strip():
            logger.warning("Attempted to store persistent memory with empty key.")
            return {"error": "Memory key cannot be empty."}

        clean_key = str(key).strip().lower()
        memories = self._read_persistent_file()

        record = {
            "key": clean_key,
            "value": value,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }

        memories[clean_key] = record
        self._write_persistent_file(memories)
        logger.info("Persistent Memory saved -> Key: '%s', Value: %s", clean_key, value)
        return record

    def retrieve(self, query: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieves relevant persistent memories matching a search query, bounded by limit.

        Args:
            query: Query string to match against key or value. If empty, returns most recent limit items.
            limit: Maximum number of memory records to return.

        Returns:
            List[Dict[str, Any]]: Bounded list of matching persistent memory records.
        """
        memories = self._read_persistent_file()
        if not memories:
            return []

        all_records = list(memories.values())

        # If query is empty, return top N recent records
        clean_query = str(query).strip().lower()
        if not clean_query:
            sorted_records = sorted(all_records, key=lambda x: x.get("timestamp", 0), reverse=True)
            return sorted_records[:limit]

        # Filter records matching query in key, value, or where key words match query terms
        matching: List[Dict[str, Any]] = []
        for record in all_records:
            k = str(record.get("key", "")).lower()
            v = str(record.get("value", "")).lower()
            m = str(record.get("metadata", "")).lower()

            key_terms = [w for w in k.replace("_", " ").split() if len(w) > 2]

            if (clean_query in k or clean_query in v or clean_query in m or
                k in clean_query or any(term in clean_query for term in key_terms)):
                matching.append(record)

        sorted_matching = sorted(matching, key=lambda x: x.get("timestamp", 0), reverse=True)
        return sorted_matching[:limit]

    def forget(self, key: str) -> bool:
        """
        Removes a persistent memory item by its key.

        Args:
            key: Key identifier to remove.

        Returns:
            bool: True if key was found and removed, False otherwise.
        """
        if not key or not str(key).strip():
            return False

        clean_key = str(key).strip().lower()
        memories = self._read_persistent_file()

        if clean_key in memories:
            del memories[clean_key]
            self._write_persistent_file(memories)
            logger.info("Persistent Memory removed -> Key: '%s'", clean_key)
            return True

        logger.info("Persistent Memory key not found -> Key: '%s'", clean_key)
        return False

    def list_memory(self) -> Dict[str, Any]:
        """
        Lists all persistent memories stored.

        Returns:
            Dict[str, Any]: Map of stored keys and values.
        """
        memories = self._read_persistent_file()
        return {k: v.get("value") for k, v in memories.items()}

    def clear_memory(self) -> None:
        """
        Clears all persistent memory entries.
        """
        self._write_persistent_file({})
        logger.info("Cleared all persistent memories.")

    # -------------------------------------------------------------------------
    # SHORT-TERM MEMORY OPERATIONS
    # -------------------------------------------------------------------------

    def add_short_term_turn(self, role: str, content: str) -> None:
        """
        Adds a conversation turn to bounded short-term in-session memory.

        Args:
            role: Participant role ('user' or 'assistant').
            content: Text content of the turn.
        """
        self.short_term_history.append({"role": role, "content": content})
        if len(self.short_term_history) > self.max_short_term_turns:
            overflow = len(self.short_term_history) - self.max_short_term_turns
            self.short_term_history = self.short_term_history[overflow:]

    def get_short_term_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        Retrieves recent short-term conversation turns bounded by limit.

        Args:
            limit: Maximum turns to return.

        Returns:
            List[Dict[str, str]]: List of turn dicts containing 'role' and 'content'.
        """
        return self.short_term_history[-limit:]

    def clear_short_term(self) -> None:
        """
        Clears short-term in-session conversation history.
        """
        self.short_term_history.clear()
