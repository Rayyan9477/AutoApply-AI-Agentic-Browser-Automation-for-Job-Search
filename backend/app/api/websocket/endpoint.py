"""WebSocket endpoint for real-time client communication (ticket-authenticated)."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.websocket.events import manager
from app.api.websocket.subscriber import forward_user_events
from app.config.settings import get_settings
from app.core.exceptions import AuthError
from app.core.security import decode_token
from app.db.redis import get_redis

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Main WebSocket endpoint for real-time updates.

    Authenticated with a short-lived ticket (``?ticket=``) validated before ``accept()``.
    While connected, a background task subscribes to the user's Redis channel and forwards
    worker-published progress events to this socket (the cross-process bridge).
    """
    # Origin check (defense-in-depth).
    origin = ws.headers.get("origin", "")
    allowed = get_settings().cors_origins
    if origin and origin not in allowed:
        await ws.close(code=4003, reason="Origin not allowed")
        return

    # Ticket authentication before accepting the connection.
    ticket = ws.query_params.get("ticket", "")
    try:
        payload = decode_token(ticket, expected_type="ws_ticket")
    except AuthError:
        await ws.close(code=4401, reason="Invalid or missing ticket")
        return
    user_id = payload.get("sub", "")

    await manager.connect(ws, user_id)

    # Forward this user's published progress events to the socket (if Redis is available).
    redis = get_redis()
    sub_task: asyncio.Task[Any] | None = None
    if redis is not None:
        sub_task = asyncio.create_task(forward_user_events(redis, user_id, ws))

    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await manager.send_to(ws, {"type": "pong", "payload": {}})
            else:
                logger.debug("ws_message_received", user_id=user_id, data=data[:100])
    except WebSocketDisconnect:
        pass
    finally:
        if sub_task is not None:
            sub_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await sub_task
        await manager.disconnect(ws, user_id)
