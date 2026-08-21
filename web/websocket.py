"""
JARVIS Web Dashboard WebSocket Connection Manager.

Manages active WebSocket client connections and provides thread-safe, non-blocking
event broadcasting for real-time dashboard updates.
"""

import asyncio
import json
import logging
from typing import Any, Dict, Set
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketManager:
    """
    Manager for handling active WebSocket client connections and event broadcasting.
    """

    def __init__(self) -> None:
        """
        Initializes the WebSocketManager.
        """
        self.active_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        """
        Accepts and registers a new client WebSocket connection.

        Args:
            websocket: Incoming WebSocket connection.
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
        logger.info("WebSocket client connected. Total clients: %d", len(self.active_connections))

    async def disconnect(self, websocket: WebSocket) -> None:
        """
        Removes a client WebSocket connection from active set.

        Args:
            websocket: Disconnected WebSocket connection.
        """
        async with self._lock:
            self.active_connections.discard(websocket)
        logger.info("WebSocket client disconnected. Remaining clients: %d", len(self.active_connections))

    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcasts a JSON message to all active WebSocket clients asynchronously.
        Handles disconnected or stale client connections safely without raising exceptions.

        Args:
            message: Event dictionary to broadcast.
        """
        if not self.active_connections:
            return

        payload = json.dumps(message, default=str)
        disconnected: Set[WebSocket] = set()

        async with self._lock:
            connections = list(self.active_connections)

        for connection in connections:
            try:
                await connection.send_text(payload)
            except (WebSocketDisconnect, RuntimeError, Exception) as e:
                logger.debug("Failed to send WebSocket message to client: %s. Marking for removal.", e)
                disconnected.add(connection)

        if disconnected:
            async with self._lock:
                for dead_conn in disconnected:
                    self.active_connections.discard(dead_conn)


# Global WebSocket Manager singleton instance
ws_manager = WebSocketManager()
