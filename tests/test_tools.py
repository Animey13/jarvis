"""
Unit tests for the JARVIS Tool Subsystem, including ToolRegistry,
DateTimeTool, and SystemStatusTool.
"""

import pytest
from tools.registry import ToolRegistry
from tools.system_tools import DateTimeTool, SystemStatusTool


@pytest.mark.asyncio
async def test_tool_registry_registration() -> None:
    """
    Verifies that tools can be registered, retrieved, and listed by ToolRegistry.
    """
    registry = ToolRegistry()
    datetime_tool = DateTimeTool()
    status_tool = SystemStatusTool()

    registry.register_tool(datetime_tool)
    registry.register_tool(status_tool)

    # Retrieval
    assert registry.get_tool("get_current_datetime") is datetime_tool
    assert registry.get_tool("get_system_status") is status_tool
    assert registry.get_tool("nonexistent_tool") is None

    # Retrieve all tools
    all_tools = registry.get_all_tools()
    assert len(all_tools) == 2
    assert datetime_tool in all_tools
    assert status_tool in all_tools


def test_tool_registry_prompt_generation() -> None:
    """
    Verifies that the prompt description returns instructions with registered tool details.
    """
    registry = ToolRegistry()
    assert "No available local system tools." in registry.get_tools_prompt_description()

    registry.register_tool(DateTimeTool())
    prompt = registry.get_tools_prompt_description()
    assert "get_current_datetime" in prompt
    assert "[TOOL: tool_name, arg1=val1, arg2=val2]" in prompt


def test_tool_registry_parsing() -> None:
    """
    Checks that tool bracket tags are properly recognized and parsed.
    """
    registry = ToolRegistry()

    # Match simple tool call
    match = registry.parse_tool_call("Let me check that. [TOOL: get_system_status]")
    assert match is not None
    name, args = match
    assert name == "get_system_status"
    assert args == {}

    # Match tool call with single argument
    match = registry.parse_tool_call("Wait a moment... [TOOL: get_weather, location=London]")
    assert match is not None
    name, args = match
    assert name == "get_weather"
    assert args == {"location": "London"}

    # Match tool call with multiple arguments (with dynamic typed casting)
    match = registry.parse_tool_call("[TOOL: process_data, count=42, ratio=3.14, name='JARVIS']")
    assert match is not None
    name, args = match
    assert name == "process_data"
    assert args == {"count": 42, "ratio": 3.14, "name": "JARVIS"}

    # No match
    assert registry.parse_tool_call("This contains no tags.") is None


@pytest.mark.asyncio
async def test_datetime_tool_execution() -> None:
    """
    Checks that the DateTimeTool returns valid current timezone-aware timestamp and formatted text.
    """
    tool = DateTimeTool()
    assert tool.name == "get_current_datetime"
    assert "Retrieves the current local date" in tool.description

    result = await tool.execute()
    assert isinstance(result, dict)
    assert "iso_timestamp" in result
    assert "weekday" in result
    assert "friendly_text" in result
    assert len(result["weekday"]) > 0
    assert len(result["friendly_text"]) > 0


@pytest.mark.asyncio
async def test_system_status_tool_execution() -> None:
    """
    Checks that the SystemStatusTool gathers local CPU, memory, disk, and uptime metrics.
    """
    tool = SystemStatusTool()
    assert tool.name == "get_system_status"

    result = await tool.execute()
    assert isinstance(result, dict)
    assert "cpu_load_averages" in result
    assert "memory" in result
    assert "disk" in result
    assert "uptime_seconds" in result

    # Check structure of nested status dictionaries
    cpu = result["cpu_load_averages"]
    assert "1_min" in cpu
    assert "5_min" in cpu
    assert "15_min" in cpu

    mem = result["memory"]
    assert "total_gb" in mem
    assert "available_gb" in mem
    assert "used_gb" in mem

    disk = result["disk"]
    assert "total_gb" in disk
    assert "used_gb" in disk
    assert "free_gb" in disk


@pytest.mark.asyncio
async def test_tool_registry_execution() -> None:
    """
    Checks that executing a tool through the registry succeeds and handles errors cleanly.
    """
    registry = ToolRegistry()
    registry.register_tool(DateTimeTool())

    # Successful call
    res = await registry.execute_tool("get_current_datetime")
    assert isinstance(res, dict)
    assert "iso_timestamp" in res

    # Unregistered tool call
    err_res = await registry.execute_tool("unknown")
    assert "is not registered" in err_res
