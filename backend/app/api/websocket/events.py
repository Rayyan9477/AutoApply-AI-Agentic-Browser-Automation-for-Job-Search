"""WebSocket connection manager for real-time event broadcasting."""

import json
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections and message broadcasting.

    Provides connect/disconnect lifecycle, targeted sends, and
    broadcast to all connected clients.
    """

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    @property
    def active_count(self) -> int:
        """Number of currently connected clients."""
        return len(self._connections)

    async def connect(self, ws: WebSocket) -> None:
        """Accept and register a new WebSocket connection.

        Args:
            ws: The incoming WebSocket connection.
        """
        await ws.accept()
        self._connections.append(ws)
        logger.info("ws_connected", active=self.active_count)

    async def disconnect(self, ws: WebSocket) -> None:
        """Remove a WebSocket connection from the active set.

        Args:
            ws: The WebSocket connection to remove.
        """
        if ws in self._connections:
            self._connections.remove(ws)
        logger.info("ws_disconnected", active=self.active_count)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to all connected clients.

        Disconnected clients are silently removed.

        Args:
            message: Dict to serialize and send as JSON text.
        """
        payload = json.dumps(message)
        stale: list[WebSocket] = []

        for ws in self._connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)

        for ws in stale:
            await self.disconnect(ws)

    async def send_to(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a specific client.

        Args:
            ws: Target WebSocket connection.
            message: Dict to serialize and send as JSON text.
        """
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            await self.disconnect(ws)


manager = ConnectionManager()
