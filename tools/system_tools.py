"""
JARVIS System Tools Module.

Implements concrete system tools conforming to the BaseTool interface:
- DateTimeTool: Retrieves local, timezone-aware current date and time.
- SystemStatusTool: Queries local Ubuntu diagnostics (CPU load, memory, disk, and uptime).
"""

import datetime
import logging
import os
import shutil
from typing import Any, Dict

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
            "Use this when the user asks 'What time is it?', 'What day is it?', or "
            "any time/date queries."
        )

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Executes the date time retrieval.

        Returns:
            Dict[str, Any]: Dictionary containing local ISO-formatted date,
                            weekday, and a pre-formatted friendly text string.
        """
        now = datetime.datetime.now().astimezone()
        friendly_str = now.strftime("%A, %B %d, %Y, %I:%M:%S %p %Z")
        return {
            "iso_timestamp": now.isoformat(),
            "weekday": now.strftime("%A"),
            "friendly_text": friendly_str,
        }


class SystemStatusTool(BaseTool):
    """
    Tool to retrieve system diagnostics for Ubuntu platforms using Python standard libraries.
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
        """Gets the 1, 5, and 15-minute CPU load averages using os.getloadavg."""
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
                with open("/proc/meminfo", "r") as f:
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
                with open("/proc/uptime", "r") as f:
                    uptime_seconds = float(f.readline().split()[0])
                    return round(uptime_seconds, 1)
        except Exception as e:
            logger.warning("Failed to retrieve system uptime: %s", e)
        return 0.0
