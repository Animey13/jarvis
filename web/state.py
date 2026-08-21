"""
JARVIS Web State Manager & Event Bus.

Coordinates live application references, status aggregation, event logging,
and system event publishing across WebSockets and REST APIs.
"""

import asyncio
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional

from web.websocket import ws_manager

logger = logging.getLogger(__name__)


class EventBus:
    """
    Central event bus for publishing structured application events to WebSockets and log feeds.
    """

    def __init__(self, max_history: int = 100) -> None:
        """
        Initializes the EventBus.

        Args:
            max_history: Maximum number of recent events kept in memory buffer.
        """
        self.max_history = max_history
        self.event_history: List[Dict[str, Any]] = []
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def publish(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Publishes a structured event, logs it, appends to history, and broadcasts to WebSockets.

        Args:
            event_type: Type identifier (e.g. 'state_change', 'transcription', 'user_message').
            data: Main event data dict.
            metadata: Optional additional metadata dict.

        Returns:
            Dict[str, Any]: Constructed event dictionary.
        """
        event = {
            "type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
            "metadata": metadata or {}
        }

        # Append to bounded event history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Broadcast asynchronously over WebSockets without blocking the caller
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(ws_manager.broadcast(event))
        except RuntimeError:
            # Fallback if no running asyncio event loop in thread context
            pass

        return event

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Returns recent published events bounded by limit.

        Args:
            limit: Maximum events to return.

        Returns:
            List[Dict[str, Any]]: List of recent event dicts.
        """
        return self.event_history[-limit:]

    def clear_history(self) -> None:
        """Clears the event history buffer."""
        self.event_history.clear()


class WebStateManager:
    """
    Holds live application references and provides system status aggregation for the Web API.
    """

    def __init__(self) -> None:
        """
        Initializes the WebStateManager.
        """
        self.start_time: float = time.time()
        self.assistant: Optional[Any] = None
        self.speech_manager: Optional[Any] = None
        self.jarvis_core: Optional[Any] = None
        self.memory_manager: Optional[Any] = None
        self.tool_registry: Optional[Any] = None
        self.tool_execution_history: List[Dict[str, Any]] = []

    def set_references(
        self,
        assistant: Optional[Any] = None,
        speech_manager: Optional[Any] = None,
        jarvis_core: Optional[Any] = None,
        memory_manager: Optional[Any] = None,
        tool_registry: Optional[Any] = None
    ) -> None:
        """
        Binds live application component instances.
        """
        if assistant is not None:
            self.assistant = assistant
        if speech_manager is not None:
            self.speech_manager = speech_manager
        if jarvis_core is not None:
            self.jarvis_core = jarvis_core
        if memory_manager is not None:
            self.memory_manager = memory_manager
        if tool_registry is not None:
            self.tool_registry = tool_registry

    def record_tool_execution(self, name: str, args: Dict[str, Any], status: str, result_summary: str) -> None:
        """
        Records a tool execution event for dashboard visibility.
        """
        record = {
            "name": name,
            "args": args,
            "status": status,
            "summary": result_summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.tool_execution_history.append(record)
        if len(self.tool_execution_history) > 50:
            self.tool_execution_history.pop(0)

    def get_uptime_seconds(self) -> float:
        """Returns application uptime in seconds."""
        return round(time.time() - self.start_time, 1)


# Global instances
event_bus = EventBus()
web_state = WebStateManager()
