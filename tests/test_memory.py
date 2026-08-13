"""
Unit tests for the JARVIS Memory Subsystem.
"""

from pathlib import Path
import pytest

from memory.local_json import LocalJSONMemory


def test_local_json_memory_initialization(tmp_path: Path) -> None:
    """Verifies that LocalJSONMemory initializes with correct file locations."""
    mem_file = tmp_path / "test_memory.json"
    mem = LocalJSONMemory(file_path=str(mem_file))
    assert mem.file_path == mem_file


@pytest.mark.asyncio
async def test_local_json_memory_store_and_retrieve(tmp_path: Path) -> None:
    """Verifies storing and retrieving conversational turns from LocalJSONMemory."""
    mem_file = tmp_path / "test_memory.json"
    mem = LocalJSONMemory(file_path=str(mem_file))

    # Store records
    await mem.store("Hello", {"role": "user"})
    await mem.store("Hi there", {"role": "assistant"})
    await mem.store("What is 2+2?", {"role": "user"})

    # 1. Retrieve all turns (limit=5)
    turns = await mem.retrieve("", limit=5)
    assert len(turns) == 3
    assert turns[0]["content"] == "Hello"
    assert turns[0]["metadata"]["role"] == "user"
    assert turns[1]["content"] == "Hi there"
    assert turns[2]["content"] == "What is 2+2?"

    # 2. Retrieve with a limit (limit=2)
    turns_limited = await mem.retrieve("", limit=2)
    assert len(turns_limited) == 2
    assert turns_limited[0]["content"] == "Hi there"
    assert turns_limited[1]["content"] == "What is 2+2?"

    # 3. Retrieve with query filter
    turns_query = await mem.retrieve("what")
    assert len(turns_query) == 1
    assert turns_query[0]["content"] == "What is 2+2?"


@pytest.mark.asyncio
async def test_local_json_memory_clear(tmp_path: Path) -> None:
    """Verifies clearing memory file records."""
    mem_file = tmp_path / "test_memory.json"
    mem = LocalJSONMemory(file_path=str(mem_file))

    await mem.store("Hello", {"role": "user"})
    turns_before = await mem.retrieve("")
    assert len(turns_before) == 1

    # Clear records
    await mem.clear()
    turns_after = await mem.retrieve("")
    assert len(turns_after) == 0
