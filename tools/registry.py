"""
JARVIS Tool Registry Module.

Provides a thread-safe registry to register, manage, discover, parse, validate,
and execute custom system tools conforming to the BaseTool interface.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Registry that maintains all registered system tools and validates/executes them.
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
        logger.info("Registered tool '%s': %s", name, tool.description[:60] + "...")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """
        Retrieves a registered tool by its name.

        Args:
            name: Identifying name of the tool (case-insensitive).

        Returns:
            Optional[BaseTool]: Registered tool instance if found, otherwise None.
        """
        if not name or not isinstance(name, str):
            return None
        return self._tools.get(name.strip().lower())

    def get_all_tools(self) -> List[BaseTool]:
        """
        Returns a list of all registered tool instances.

        Returns:
            List[BaseTool]: List of available tools.
        """
        return list(self._tools.values())

    def validate_arguments(self, name: str, args: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validates arguments passed for a specific tool against its defined parameters schema.

        Args:
            name: Tool name.
            args: Provided argument dictionary.

        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        tool = self.get_tool(name)
        if not tool:
            return False, f"Unknown tool '{name}'."

        if not isinstance(args, dict):
            return False, "Malformed arguments: Arguments must be a dictionary."

        schema = tool.parameters
        if not schema:
            # Tool accepts any or no arguments
            return True, None

        # Check required parameters in schema if specified
        required_params = [k for k, v in schema.items() if v.get("required", False)]
        for param in required_params:
            if param not in args:
                return False, f"Missing required argument '{param}' for tool '{tool.name}'."

        return True, None

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
            params_desc = ""
            if tool.parameters:
                params_list = [f"{k}: {v.get('type', 'any')}" for k, v in tool.parameters.items()]
                params_desc = f" (Parameters: {', '.join(params_list)})"
            prompt_lines.append(f"- Name: {tool.name}{params_desc}")
            prompt_lines.append(f"  Description: {tool.description}")

        prompt_lines.append(
            "\nTo invoke a tool, output a single-line command in this exact bracket tag format:\n"
            "[TOOL: tool_name, arg1=val1, arg2=val2]\n"
            "When a tool is executed, you will be given the output "
            "and can then answer the user's question with actual system data."
        )
        return "\n".join(prompt_lines)

    def parse_tool_call(self, text: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        Scans a text response from the LLM to identify and parse a bracket tag tool call.
        e.g. '[TOOL: get_system_status]' or '[TOOL: list_files, path=.]'

        Args:
            text: Text to search.

        Returns:
            Optional[Tuple[str, Dict[str, Any]]]: Tuple of (tool_name, parsed_args) if a valid
                                                 call is found, otherwise None.
        """
        if not text or not isinstance(text, str):
            return None

        # Regex to match bracket tag: [TOOL: tool_name, arg1=val1, ...]
        match = re.search(r"\[TOOL:\s*([\w_-]+)(?:,\s*([^]]+))?\]", text, re.IGNORECASE)
        if not match:
            return None

        tool_name = match.group(1).strip().lower()
        args_str = match.group(2)
        args: Dict[str, Any] = {}

        if args_str:
            # Parse key-value pairs separated by commas
            # e.g., "arg1=val1, arg2=val2"
            pairs = re.findall(r"([\w_-]+)\s*=\s*([^,]+)", args_str)
            for key, val in pairs:
                clean_val = val.strip().strip("'\"")
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
        Asynchronously executes a registered tool with argument validation and error handling.

        Args:
            name: Identifying name of the tool.
            **kwargs: Dynamic key-value parameters.

        Returns:
            Any: Execution output results dict, or error dictionary on failure.
        """
        tool = self.get_tool(name)
        if not tool:
            err_msg = f"Tool '{name}' is not registered with the system."
            logger.error("Tool execution failed: %s", err_msg)
            return {"status": "error", "error": err_msg}

        is_valid, validation_error = self.validate_arguments(name, kwargs)
        if not is_valid:
            err_msg = f"Argument validation failed for tool '{name}': {validation_error}"
            logger.error(err_msg)
            return {"status": "error", "error": err_msg}

        logger.info("TOOL CALL START -> Name: '%s', Arguments: %s", name, kwargs)
        try:
            result = await tool.execute(**kwargs)
            logger.info("TOOL CALL SUCCESS -> Name: '%s', Result Summary: %s", name, str(result)[:100])
            return {"status": "success", "result": result}
        except Exception as e:
            err_msg = f"Failed to execute tool '{name}': {e}"
            logger.exception("TOOL CALL ERROR -> Name: '%s': %s", name, e)
            return {"status": "error", "error": err_msg}
