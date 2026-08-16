"""
Unit tests for the Phase 4 JARVIS Memory System.
Tests storing memory, retrieving memory, deleting memory, persistence across reloads,
corrupted JSON file handling, bounded retrieval, explicit memory tools, and JarvisCore integration.
"""

from unittest import mock
import pytest
from app.core import JarvisCore
from config.config import load_settings
from memory.manager import MemoryManager
from tools.system_tools import ForgetMemoryTool, QueryMemoryTool, RememberTool


def test_remember_and_retrieve(tmp_path) -> None:
    """
    Verifies storing facts in persistent memory and retrieving them by query.
    """
    mem_file = tmp_path / "persistent_memory.json"
    mgr = MemoryManager(file_path=str(mem_file))

    # Store memory
    rec = mgr.remember("user_name", "Alex")
    assert rec["key"] == "user_name"
    assert rec["value"] == "Alex"

    # Store second memory
    mgr.remember("coffee_pref", "black coffee with no sugar")

    # Retrieve matching query
    results = mgr.retrieve("coffee")
    assert len(results) == 1
    assert results[0]["key"] == "coffee_pref"
    assert results[0]["value"] == "black coffee with no sugar"


def test_forget_and_list_memory(tmp_path) -> None:
    """
    Verifies deleting facts from persistent memory and listing memories.
    """
    mem_file = tmp_path / "persistent_memory.json"
    mgr = MemoryManager(file_path=str(mem_file))

    mgr.remember("key1", "val1")
    mgr.remember("key2", "val2")

    listed = mgr.list_memory()
    assert listed == {"key1": "val1", "key2": "val2"}

    # Forget key1
    forgot = mgr.forget("key1")
    assert forgot is True
    assert mgr.list_memory() == {"key2": "val2"}

    # Forget nonexistent key
    forgot_nonexistent = mgr.forget("nonexistent")
    assert forgot_nonexistent is False


def test_persistence_across_reloads(tmp_path) -> None:
    """
    Verifies that persistent memory survives instance reloads by reading from disk.
    """
    mem_file = tmp_path / "persistent_memory.json"

    # Instance 1: write fact
    mgr1 = MemoryManager(file_path=str(mem_file))
    mgr1.remember("project_name", "JARVIS AI")

    # Instance 2: read from same file path
    mgr2 = MemoryManager(file_path=str(mem_file))
    retrieved = mgr2.retrieve("project")
    assert len(retrieved) == 1
    assert retrieved[0]["value"] == "JARVIS AI"


def test_corrupted_file_handling(tmp_path) -> None:
    """
    Verifies that a corrupted persistent memory JSON file is backed up and handled gracefully without crashing.
    """
    mem_file = tmp_path / "persistent_memory.json"
    # Write invalid JSON content
    mem_file.write_text("CORRUPTED_NOT_JSON {{{", encoding="utf-8")

    mgr = MemoryManager(file_path=str(mem_file))

    # Retrieve should not crash and return empty list
    retrieved = mgr.retrieve()
    assert retrieved == []

    # Verify memory store recovers and can remember new facts
    mgr.remember("new_fact", "recovered")
    assert mgr.list_memory() == {"new_fact": "recovered"}


def test_bounded_retrieval_limit(tmp_path) -> None:
    """
    Verifies that memory retrieval limits the number of returned records.
    """
    mem_file = tmp_path / "persistent_memory.json"
    mgr = MemoryManager(file_path=str(mem_file))

    for i in range(10):
        mgr.remember(f"key_{i}", f"value_{i}")

    # Bounded retrieval limit = 3
    results = mgr.retrieve(limit=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_memory_tools_execution(tmp_path) -> None:
    """
    Verifies execution of explicit memory tools (RememberTool, QueryMemoryTool, ForgetMemoryTool).
    """
    mem_file = tmp_path / "persistent_memory.json"
    mgr = MemoryManager(file_path=str(mem_file))

    remember_tool = RememberTool(memory_manager=mgr)
    query_tool = QueryMemoryTool(memory_manager=mgr)
    forget_tool = ForgetMemoryTool(memory_manager=mgr)

    # Execute remember_tool
    res_rem = await remember_tool.execute(key="favorite_color", value="blue")
    assert res_rem["status"] == "memory_stored"

    # Execute query_tool
    res_q = await query_tool.execute(query="color")
    assert res_q["count"] == 1
    assert res_q["memories"][0]["value"] == "blue"

    # Execute forget_tool
    res_f = await forget_tool.execute(key="favorite_color")
    assert res_f["removed"] == True


@pytest.mark.asyncio
async def test_jarvis_core_memory_integration(tmp_path) -> None:
    """
    Verifies that JarvisCore retrieves relevant persistent memories and includes them in the prompt.
    """
    mem_file = tmp_path / "persistent_memory.json"
    mgr = MemoryManager(file_path=str(mem_file))
    mgr.remember("user_nickname", "Tony")

    settings = load_settings()
    mock_llm = mock.AsyncMock()
    mock_llm.model_name = "llama3:8b"
    mock_llm.api_base = "http://localhost:11434"
    mock_llm.timeout = 30.0
    mock_llm.generate.return_value = "Hello Tony!"

    core = JarvisCore(settings=settings, llm_client=mock_llm, memory_manager=mgr)

    response = await core.respond("What is my nickname?")

    assert response == "Hello Tony!"
    call_args = mock_llm.generate.call_args[1]
    prompt_sent = call_args["prompt"]
    assert "Relevant Persistent Facts & Preferences:" in prompt_sent
    assert "user_nickname: Tony" in prompt_sent
