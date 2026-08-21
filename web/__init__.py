"""
JARVIS Web Dashboard Subpackage.

Provides a local FastAPI web server, WebSocket real-time event bus, REST API routes,
Pydantic schemas, and a responsive frontend dashboard.
"""

from web.state import event_bus, web_state
from web.websocket import ws_manager

__all__ = [
    "event_bus",
    "web_state",
    "ws_manager",
]
