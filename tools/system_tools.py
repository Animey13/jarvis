"""
JARVIS System Tools Module.

Implements safe, modular system tools conforming to the BaseTool interface:
- DateTimeTool: Retrieves local, timezone-aware current date and time.
- CalculatorTool: Safely evaluates basic mathematical expressions using AST parsing.
- SystemStatusTool: Queries local Ubuntu diagnostics (CPU load, memory, disk, and uptime).
- ListFilesTool: Safely lists files and directories in a requested path.
- ReadFileTool: Safely reads text contents of files with size enforcement.
- RestrictedCommandTool: Executes strictly allowlisted, non-shell OS commands safely.
- RememberTool: Explicitly stores an intentional fact into persistent memory.
- QueryMemoryTool: Queries stored persistent facts and memories.
- ForgetMemoryTool: Deletes a stored fact from persistent memory.
"""

import ast
import asyncio
import datetime
import logging
import operator
import os
from pathlib import Path
import shutil
from typing import Any, Dict, Optional

from tools.base import BaseTool

logger = logging.getLogger(__name__)


class DateTimeTool(BaseTool):
    """
    Tool to retrieve the current date and time in a friendly, local-aware format.
    """

    @property
    def name(self) -> str:
        return "get_current_datetime"

    @property
    def description(self) -> str:
        return (
            "Retrieves the current local date, time, and timezone. "
            "Use this when asked 'What time is it?', 'What day is it?', or any date/time query."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {}

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes date and time retrieval.

        Returns:
            Dict[str, Any]: Local ISO-formatted timestamp and friendly string.
        """
        now = datetime.datetime.now().astimezone()
        friendly_str = now.strftime("%A, %B %d, %Y, %I:%M:%S %p %Z")
        return {
            "iso_timestamp": now.isoformat(),
            "weekday": now.strftime("%A"),
            "friendly_text": friendly_str,
        }


class CalculatorTool(BaseTool):
    """
    Safely evaluates basic arithmetic expressions without arbitrary code execution risk.
    """

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Evaluates a mathematical expression safely (e.g. '12 * (3 + 4)'). "
            "Use this for any mathematical calculation requests."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "expression": {
                "type": "string",
                "required": True,
                "description": "Mathematical expression string to calculate."
            }
        }

    async def execute(self, expression: str = "", **kwargs: Any) -> Dict[str, Any]:
        """
        Safely evaluates an arithmetic expression using AST parsing.

        Args:
            expression: Arithmetic string to calculate.

        Returns:
            Dict[str, Any]: Calculation result or error details.
        """
        if not expression or not str(expression).strip():
            return {"error": "Missing mathematical expression."}

        clean_expr = str(expression).strip()
        try:
            result = self._safe_eval(clean_expr)
            return {"expression": clean_expr, "result": result}
        except Exception as e:
            logger.warning("Calculator evaluation failed for '%s': %s", clean_expr, e)
            return {"expression": clean_expr, "error": f"Failed to evaluate expression: {e}"}

    def _safe_eval(self, expr: str) -> float:
        """Parses and evaluates an arithmetic expression safely using AST."""
        allowed_operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.FloorDiv: operator.floordiv,
            ast.Mod: operator.mod,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }

        def eval_node(node: Any) -> Any:
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
                return node.value
            elif isinstance(node, ast.BinOp):
                op_type = type(node.op)
                if op_type in allowed_operators:
                    return allowed_operators[op_type](eval_node(node.left), eval_node(node.right))
            elif isinstance(node, ast.UnaryOp):
                op_type = type(node.op)
                if op_type in allowed_operators:
                    return allowed_operators[op_type](eval_node(node.operand))
            raise ValueError(f"Unsupported syntax or operator in expression: '{expr}'")

        tree = ast.parse(expr, mode='eval')
        res = eval_node(tree.body)
        return float(res)


class SystemStatusTool(BaseTool):
    """
    Tool to retrieve system diagnostics for Ubuntu platforms using standard OS endpoints.
    """

    @property
    def name(self) -> str:
        return "get_system_status"

    @property
    def description(self) -> str:
        return (
            "Queries system diagnostics on the local machine: CPU load, "
            "RAM consumption (total, available, used), disk space, and system uptime. "
            "Use this when asked 'How is the system running?' or 'System diagnostics'."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {}

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Gathers system information from standard OS endpoints and returns them.

        Returns:
            Dict[str, Any]: Current system status parameters.
        """
        status: Dict[str, Any] = {
            "cpu_load_averages": self._get_cpu_load(),
            "memory": self._get_memory_usage(),
            "disk": self._get_disk_usage(),
            "uptime_seconds": self._get_uptime(),
        }
        return status

    def _get_cpu_load(self) -> Dict[str, float]:
        """Gets CPU load averages using os.getloadavg."""
        try:
            load1, load5, load15 = os.getloadavg()
            return {"1_min": round(load1, 2), "5_min": round(load5, 2), "15_min": round(load15, 2)}
        except Exception as e:
            logger.warning("Failed to retrieve CPU load: %s", e)
            return {"1_min": 0.0, "5_min": 0.0, "15_min": 0.0}

    def _get_memory_usage(self) -> Dict[str, float]:
        """Reads RAM statistics by parsing /proc/meminfo."""
        mem_info: Dict[str, float] = {"total_gb": 0.0, "available_gb": 0.0, "used_gb": 0.0, "percent_used": 0.0}
        try:
            if os.path.exists("/proc/meminfo"):
                total_kb = 0.0
                avail_kb = 0.0
                with open("/proc/meminfo", "r", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("MemTotal:"):
                            total_kb = float(line.split()[1])
                        elif line.startswith("MemAvailable:"):
                            avail_kb = float(line.split()[1])

                if total_kb > 0:
                    total_gb = total_kb / (1024 * 1024)
                    avail_gb = avail_kb / (1024 * 1024)
                    used_gb = total_gb - avail_gb
                    percent_used = (used_gb / total_gb) * 100.0

                    mem_info["total_gb"] = round(total_gb, 2)
                    mem_info["available_gb"] = round(avail_gb, 2)
                    mem_info["used_gb"] = round(used_gb, 2)
                    mem_info["percent_used"] = round(percent_used, 1)
        except Exception as e:
            logger.warning("Failed to parse /proc/meminfo: %s", e)
        return mem_info

    def _get_disk_usage(self) -> Dict[str, float]:
        """Fetches root disk usage statistics using shutil.disk_usage."""
        disk_info: Dict[str, float] = {"total_gb": 0.0, "used_gb": 0.0, "free_gb": 0.0, "percent_used": 0.0}
        try:
            total, used, free = shutil.disk_usage("/")
            total_gb = total / (1024**3)
            used_gb = used / (1024**3)
            free_gb = free / (1024**3)
            percent_used = (used / total) * 100.0 if total > 0 else 0.0

            disk_info["total_gb"] = round(total_gb, 2)
            disk_info["used_gb"] = round(used_gb, 2)
            disk_info["free_gb"] = round(free_gb, 2)
            disk_info["percent_used"] = round(percent_used, 1)
        except Exception as e:
            logger.warning("Failed to retrieve disk usage: %s", e)
        return disk_info

    def _get_uptime(self) -> float:
        """Retrieves system uptime in seconds from /proc/uptime."""
        try:
            if os.path.exists("/proc/uptime"):
                with open("/proc/uptime", "r", encoding="utf-8") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return round(uptime_seconds, 1)
        except Exception as e:
            logger.warning("Failed to retrieve system uptime: %s", e)
        return 0.0


class ListFilesTool(BaseTool):
    """
    Tool to safely list files and subdirectories in a specified directory path.
    """

    @property
    def name(self) -> str:
        return "list_files"

    @property
    def description(self) -> str:
        return "Lists files and subdirectories in a requested local directory path."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "required": False,
                "description": "Directory path to list (defaults to '.')."
            }
        }

    async def execute(self, path: str = ".", **kwargs: Any) -> Dict[str, Any]:
        """
        Lists files in a requested directory path.

        Args:
            path: Target directory path string.

        Returns:
            Dict[str, Any]: List of directory items or error details.
        """
        target_path = Path(path).resolve()
        if not target_path.exists():
            return {"path": str(target_path), "error": "Directory path does not exist."}
        if not target_path.is_dir():
            return {"path": str(target_path), "error": "Specified path is not a directory."}

        try:
            entries = []
            for entry in os.scandir(target_path):
                entries.append({
                    "name": entry.name,
                    "is_directory": entry.is_dir(),
                    "size_bytes": entry.stat().st_size if entry.is_file() else 0
                })
            return {"path": str(target_path), "total_items": len(entries), "items": entries[:50]}
        except Exception as e:
            return {"path": str(target_path), "error": f"Failed to list directory: {e}"}


class ReadFileTool(BaseTool):
    """
    Tool to safely read small text files.
    """

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "Reads the text contents of a requested local file path safely."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "filepath": {
                "type": "string",
                "required": True,
                "description": "Path of the text file to read."
            }
        }

    async def execute(self, filepath: str = "", **kwargs: Any) -> Dict[str, Any]:
        """
        Reads a small text file safely.

        Args:
            filepath: Target file path string.

        Returns:
            Dict[str, Any]: File content or error details.
        """
        if not filepath or not str(filepath).strip():
            return {"error": "Missing filepath argument."}

        target_path = Path(filepath).resolve()
        if not target_path.exists():
            return {"filepath": str(target_path), "error": "File does not exist."}
        if not target_path.is_file():
            return {"filepath": str(target_path), "error": "Path is not a regular file."}

        try:
            # Enforce 10KB max size limit
            file_size = target_path.stat().st_size
            if file_size > 10 * 1024:
                return {
                    "filepath": str(target_path),
                    "error": f"File size ({file_size} bytes) exceeds maximum safety limit of 10KB."
                }

            with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            return {"filepath": str(target_path), "size_bytes": file_size, "content": content}
        except Exception as e:
            return {"filepath": str(target_path), "error": f"Failed to read file: {e}"}


class RestrictedCommandTool(BaseTool):
    """
    Tool to safely execute strictly allowlisted non-shell system commands.
    """

    ALLOWLIST = {
        "uptime": ["uptime"],
        "whoami": ["whoami"],
        "date": ["date"],
        "df": ["df", "-h"],
        "free": ["free", "-m"],
        "hostname": ["hostname"],
        "uname": ["uname", "-a"],
        "lsb_release": ["lsb_release", "-a"]
    }

    @property
    def name(self) -> str:
        return "restricted_command"

    @property
    def description(self) -> str:
        return (
            "Executes an allowlisted system command safely. "
            "Allowed commands: 'uptime', 'whoami', 'date', 'df', 'free', 'hostname', 'uname', 'lsb_release'."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "command": {
                "type": "string",
                "required": True,
                "description": "Allowed command name to execute."
            }
        }

    async def execute(self, command: str = "", **kwargs: Any) -> Dict[str, Any]:
        """
        Executes an allowlisted command safely without shell evaluation.

        Args:
            command: Command name string.

        Returns:
            Dict[str, Any]: Command output or error details.
        """
        cmd_key = str(command).strip().lower()
        if cmd_key not in self.ALLOWLIST:
            return {
                "command": command,
                "error": f"Command '{command}' is not in the restricted allowlist. Allowed: {list(self.ALLOWLIST.keys())}"
            }

        cmd_args = self.ALLOWLIST[cmd_key]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            return {
                "command": command,
                "return_code": proc.returncode,
                "stdout": stdout.decode("utf-8", errors="replace").strip(),
                "stderr": stderr.decode("utf-8", errors="replace").strip()
            }
        except Exception as e:
            return {"command": command, "error": f"Failed to execute command: {e}"}


class RememberTool(BaseTool):
    """
    Tool to explicitly store an intentional fact or preference into persistent memory.
    """

    def __init__(self, memory_manager: Optional[Any] = None) -> None:
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "remember_fact"

    @property
    def description(self) -> str:
        return (
            "Stores an intentional fact, instruction, or preference into persistent memory. "
            "Use this when asked 'Remember that...', 'Note down...', or given explicit facts."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "key": {
                "type": "string",
                "required": True,
                "description": "Short unique identifier key for the fact (e.g. 'user_name')."
            },
            "value": {
                "type": "string",
                "required": True,
                "description": "The fact or preference value to store (e.g. 'Alex')."
            }
        }

    async def execute(self, key: str = "", value: Any = "", **kwargs: Any) -> Dict[str, Any]:
        if not key or not str(key).strip():
            return {"error": "Missing required argument 'key'."}

        if self.memory_manager is None:
            from memory.manager import MemoryManager
            self.memory_manager = MemoryManager()

        rec = self.memory_manager.remember(key, value)
        return {"status": "memory_stored", "key": key, "value": value}


class QueryMemoryTool(BaseTool):
    """
    Tool to query or search stored facts in persistent memory.
    """

    def __init__(self, memory_manager: Optional[Any] = None) -> None:
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "query_memory"

    @property
    def description(self) -> str:
        return (
            "Queries or searches stored persistent memories and facts. "
            "Use this when asked 'What do you remember about...?' or 'What is my...'."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "required": False,
                "description": "Query term to filter stored memories (e.g. 'coffee')."
            }
        }

    async def execute(self, query: str = "", **kwargs: Any) -> Dict[str, Any]:
        if self.memory_manager is None:
            from memory.manager import MemoryManager
            self.memory_manager = MemoryManager()

        results = self.memory_manager.retrieve(query, limit=5)
        return {"query": query, "count": len(results), "memories": results}


class ForgetMemoryTool(BaseTool):
    """
    Tool to delete a stored fact from persistent memory.
    """

    def __init__(self, memory_manager: Optional[Any] = None) -> None:
        self.memory_manager = memory_manager

    @property
    def name(self) -> str:
        return "forget_fact"

    @property
    def description(self) -> str:
        return (
            "Deletes a stored fact or preference from persistent memory. "
            "Use this when asked 'Forget that...' or 'Delete memory for...'."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "key": {
                "type": "string",
                "required": True,
                "description": "Memory key identifier to delete (e.g. 'user_name')."
            }
        }

    async def execute(self, key: str = "", **kwargs: Any) -> Dict[str, Any]:
        if not key or not str(key).strip():
            return {"error": "Missing required argument 'key'."}

        if self.memory_manager is None:
            from memory.manager import MemoryManager
            self.memory_manager = MemoryManager()

        removed = self.memory_manager.forget(key)
        return {"key": key, "removed": removed}
