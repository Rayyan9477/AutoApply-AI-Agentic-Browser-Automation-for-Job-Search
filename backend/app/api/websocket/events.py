"""WebSocket connection manager — tracks connections per user for targeted fan-out."""

import asyncio
import json
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)

# Event types published on the per-user bus (``{"type": ..., "payload": {...}}``).
EVENT_APPLICATION_PROGRESS = "application_progress"
EVENT_JOB_SEARCH_PROGRESS = "job_search_progress"  # {search_id, platform, status, count, error}
EVENT_JOB_SEARCH_COMPLETE = "job_search_complete"  # {search_id, total, warnings, boards}


class ConnectionManager:
    """Manages active WebSocket connections, keyed by owning user.

    Connections are grouped by ``user_id`` so the Redis pub/sub subscriber can fan a
    user's events out to exactly that user's sockets (``send_to_user``). ``user_id`` is
    optional for backward compatibility / anonymous sockets.
    """

    def __init__(self) -> None:
        self._by_user: dict[str | None, set[WebSocket]] = {}
        # One lock per socket so the pub/sub subscriber task and the ping/pong handler
        # never call send_text concurrently on the same socket (which can corrupt frames).
        self._locks: dict[WebSocket, asyncio.Lock] = {}

    @property
    def active_count(self) -> int:
        """Total number of currently connected clients across all users."""
        return sum(len(conns) for conns in self._by_user.values())

    async def connect(self, ws: WebSocket, user_id: str | None = None) -> None:
        """Accept and register a new WebSocket connection for ``user_id``."""
        await ws.accept()
        self._by_user.setdefault(user_id, set()).add(ws)
        self._locks[ws] = asyncio.Lock()
        logger.info("ws_connected", user_id=user_id, active=self.active_count)

    async def disconnect(self, ws: WebSocket, user_id: str | None = None) -> None:
        """Remove a WebSocket connection (from whichever user bucket holds it)."""
        for uid, conns in list(self._by_user.items()):
            if ws in conns:
                conns.discard(ws)
                if not conns:
                    self._by_user.pop(uid, None)
        self._locks.pop(ws, None)
        logger.info("ws_disconnected", user_id=user_id, active=self.active_count)

    async def _send(self, ws: WebSocket, payload: str) -> None:
        """Serialize writes to a single socket via its per-connection lock."""
        lock = self._locks.get(ws)
        if lock is None:
            await ws.send_text(payload)
            return
        async with lock:
            await ws.send_text(payload)

    async def send_raw(self, ws: WebSocket, text: str) -> None:
        """Send an already-serialized text frame through the socket's send lock.

        Used by the Redis pub/sub subscriber task so its writes serialize with the ping/pong
        handler on the same socket (concurrent ``send_text`` corrupts frames).
        """
        await self._send(ws, text)

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a JSON message to every connected client (stale clients are removed)."""
        payload = json.dumps(message)
        for conns in list(self._by_user.values()):
            for ws in list(conns):
                try:
                    await self._send(ws, payload)
                except Exception:
                    await self.disconnect(ws)

    async def send_to_user(self, user_id: str, message: dict[str, Any]) -> None:
        """Send a JSON message to all of one user's connected clients."""
        payload = json.dumps(message)
        for ws in list(self._by_user.get(user_id, set())):
            try:
                await self._send(ws, payload)
            except Exception:
                await self.disconnect(ws, user_id)

    async def send_to(self, ws: WebSocket, message: dict[str, Any]) -> None:
        """Send a JSON message to a specific client."""
        try:
            await self._send(ws, json.dumps(message))
        except Exception:
            await self.disconnect(ws)


manager = ConnectionManager()
