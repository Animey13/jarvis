"""
Unit tests for the JARVIS Tool Subsystem, including ToolRegistry, argument validation,
and concrete safe system tools (DateTimeTool, CalculatorTool, SystemStatusTool,
ListFilesTool, ReadFileTool, RestrictedCommandTool).
"""

from unittest import mock
import pytest
from app.core import JarvisCore
from config.config import load_settings
from tools.registry import ToolRegistry
from tools.system_tools import (
    CalculatorTool,
    DateTimeTool,
    ListFilesTool,
    ReadFileTool,
    RestrictedCommandTool,
    SystemStatusTool,
)


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
    match = registry.parse_tool_call("Wait a moment... [TOOL: calculator, expression='12 * 4']")
    assert match is not None
    name, args = match
    assert name == "calculator"
    assert args == {"expression": "12 * 4"}

    # No match
    assert registry.parse_tool_call("This contains no tags.") is None


def test_tool_argument_validation() -> None:
    """
    Checks that arguments are validated against the tool's parameter schema.
    """
    registry = ToolRegistry()
    calc_tool = CalculatorTool()
    registry.register_tool(calc_tool)

    # Valid args
    valid, err = registry.validate_arguments("calculator", {"expression": "2 + 2"})
    assert valid is True
    assert err is None

    # Missing required param
    valid_missing, err_missing = registry.validate_arguments("calculator", {})
    assert valid_missing is False
    assert "Missing required argument 'expression'" in err_missing

    # Unknown tool validation
    valid_unknown, err_unknown = registry.validate_arguments("unknown_tool", {})
    assert valid_unknown is False
    assert "Unknown tool" in err_unknown


@pytest.mark.asyncio
async def test_calculator_tool_execution() -> None:
    """
    Checks safe math evaluation and error handling in CalculatorTool.
    """
    tool = CalculatorTool()
    assert tool.name == "calculator"

    # Valid math calculation
    res = await tool.execute(expression="25 * 4 - (10 / 2)")
    assert res["result"] == 95.0

    # Syntax error in math expression
    res_err = await tool.execute(expression="25 * * 4")
    assert "error" in res_err


@pytest.mark.asyncio
async def test_list_files_tool_execution(tmp_path) -> None:
    """
    Checks directory listing functionality in ListFilesTool.
    """
    tool = ListFilesTool()

    # Create test file
    test_file = tmp_path / "sample.txt"
    test_file.write_text("hello", encoding="utf-8")

    res = await tool.execute(path=str(tmp_path))
    assert res["total_items"] == 1
    assert res["items"][0]["name"] == "sample.txt"

    # Non-existent path
    res_err = await tool.execute(path="/non/existent/path/1234")
    assert "error" in res_err


@pytest.mark.asyncio
async def test_read_file_tool_execution(tmp_path) -> None:
    """
    Checks reading file content safely with ReadFileTool.
    """
    tool = ReadFileTool()

    # Create file
    test_file = tmp_path / "hello.txt"
    test_file.write_text("Hello JARVIS!", encoding="utf-8")

    res = await tool.execute(filepath=str(test_file))
    assert res["content"] == "Hello JARVIS!"
    assert res["size_bytes"] == 13

    # Non-existent file
    res_err = await tool.execute(filepath=str(tmp_path / "missing.txt"))
    assert "error" in res_err


@pytest.mark.asyncio
async def test_restricted_command_tool_execution() -> None:
    """
    Checks executing allowlisted OS commands with RestrictedCommandTool.
    """
    tool = RestrictedCommandTool()

    # Allowed command execution
    res = await tool.execute(command="uptime")
    assert res["return_code"] == 0
    assert len(res["stdout"]) > 0

    # Disallowed command execution
    res_disallowed = await tool.execute(command="rm -rf /")
    assert "error" in res_disallowed
    assert "not in the restricted allowlist" in res_disallowed["error"]


@pytest.mark.asyncio
async def test_tool_registry_execution_wrapper() -> None:
    """
    Checks that executing a tool through ToolRegistry returns structured success/error dicts.
    """
    registry = ToolRegistry()
    registry.register_tool(DateTimeTool())

    # Success wrapper
    res = await registry.execute_tool("get_current_datetime")
    assert res["status"] == "success"
    assert "iso_timestamp" in res["result"]

    # Unknown tool wrapper
    err_res = await registry.execute_tool("unknown_tool")
    assert err_res["status"] == "error"
    assert "is not registered" in err_res["error"]


@pytest.mark.asyncio
async def test_jarvis_core_tool_orchestration() -> None:
    """
    Verifies that JarvisCore parses tool call tags, executes the tool, and synthesizes the response.
    """
    settings = load_settings()
    mock_llm = mock.AsyncMock()
    mock_llm.model_name = "llama3:8b"
    mock_llm.api_base = "http://localhost:11434"
    mock_llm.timeout = 30.0

    # First call returns tool tag, second call synthesizes final answer
    mock_llm.generate.side_effect = [
        "[TOOL: calculator, expression='10 + 15']",
        "10 plus 15 is 25."
    ]

    core = JarvisCore(settings=settings, llm_client=mock_llm)

    response = await core.respond("What is 10 + 15?")

    assert response == "10 plus 15 is 25."
    assert mock_llm.generate.call_count == 2
