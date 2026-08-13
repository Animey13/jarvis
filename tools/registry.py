"""
JARVIS Tool Registry Module.

Provides a thread-safe registry to register, manage, parse, and execute
custom system tools conforming to the BaseTool interface.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry that maintains all registered system tools and parses/executes them.
    """

    def __init__(self) -> None:
        """
        Initializes the ToolRegistry.
        """
        self._tools: Dict[str, BaseTool] = {}

    def register_tool(self, tool: BaseTool) -> None:
        """
        Registers a new custom tool with the registry.

        Args:
            tool: An instance of BaseTool to register.
        """
        name = tool.name.strip().lower()
        if name in self._tools:
            logger.warning("Tool with name '%s' is already registered. Overwriting.", name)
        self._tools[name] = tool
        logger.info("Successfully registered tool: '%s' - %s", name, tool.description[:60] + "...")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Retrieves a registered tool by its name.

        Args:
            name: Identifying name of the tool (case-insensitive).

        Returns:
            Optional[BaseTool]: Registered tool instance if found, otherwise None.
        """
        return self._tools.get(name.strip().lower())

    def get_all_tools(self) -> List[BaseTool]:
        """
        Returns a list of all registered tool instances.

        Returns:
            List[BaseTool]: List of available tools.
        """
        return list(self._tools.values())

    def get_tools_prompt_description(self) -> str:
        """
        Generates a consolidated text description of all registered tools,
        formatted for inclusion in the LLM system prompt.

        Returns:
            str: Consistently formatted tools list instructions.
        """
        if not self._tools:
            return "No available local system tools."

        prompt_lines = ["You have access to the following local system tools:\n"]
        for tool in self._tools.values():
            prompt_lines.append(f"- Name: {tool.name}")
            prompt_lines.append(f"  Description: {tool.description}")

        prompt_lines.append(
            "\nTo invoke a tool, output a single-line command in this exact bracket tag format:\n"
            "[TOOL: tool_name, arg1=val1, arg2=val2]\n"
            "Keep arguments short and standard. When a tool is executed, you will be given the output "
            "and can then answer the user's question with actual system data."
        )
        return "\n".join(prompt_lines)

    def parse_tool_call(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Scans a text response from the LLM to identify and parse a bracket tag tool call.
        e.g. '[TOOL: get_system_status]' or '[TOOL: get_current_datetime]'

        Args:
            text: Text to search.

        Returns:
            Optional[Tuple[str, Dict[str, Any]]]: Tuple of (tool_name, parsed_args) if a valid
                                                 call is found, otherwise None.
        """
        # Regex to match bracket tag: [TOOL: tool_name, arg1=val1, ...]
        match = re.search(r"\[TOOL:\s*(\w+)(?:,\s*([^]]+))?\]", text, re.IGNORECASE)
        if not match:
            return None

        tool_name = match.group(1).strip().lower()
        args_str = match.group(2)
        args: Dict[str, Any] = {}

        if args_str:
            # Parse key-value pairs separated by commas
            # e.g., "arg1=val1, arg2=val2"
            pairs = re.findall(r"(\w+)\s*=\s*([^,]+)", args_str)
            for key, val in pairs:
                # Strip spaces and resolve raw string quotes if any
                clean_val = val.strip().strip("'\"")
                # Attempt to parse as float/int if numeric
                try:
                    if "." in clean_val:
                        args[key] = float(clean_val)
                    else:
                        args[key] = int(clean_val)
                except ValueError:
                    args[key] = clean_val

        return tool_name, args

    async def execute_tool(self, name: str, **kwargs: Any) -> Any:
        """
        Asynchronously executes a registered tool with the provided arguments.

        Args:
            name: Identifying name of the tool.
            **kwargs: Dynamic key-value parameters.

        Returns:
            Any: Execution output results, or error message on failure.
        """
        tool = self.get_tool(name)
        if not tool:
            err_msg = f"Error: Tool '{name}' is not registered with the system."
            logger.error(err_msg)
            return err_msg

        logger.info("Executing tool '%s' with arguments: %s", name, kwargs)
        try:
            result = await tool.execute(**kwargs)
            logger.info("Tool '%s' executed successfully.", name)
            return result
        except Exception as e:
            err_msg = f"Error: Failed to execute tool '{name}': {e}"
            logger.exception(err_msg)
            return err_msg
