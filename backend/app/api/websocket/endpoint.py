"""WebSocket endpoint for real-time client communication."""

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.websocket.events import manager
from app.config.settings import get_settings

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket) -> None:
    """Main WebSocket endpoint for real-time updates.

    Clients connect here to receive live events such as:
    - Application status changes
    - Job search progress
    - Queue processing updates

    Supports ping/pong keep-alive from the client side.
    """
    # Validate origin before accepting the connection
    origin = ws.headers.get("origin", "")
    allowed = get_settings().cors_origins
    if origin and origin not in allowed:
        await ws.close(code=4003, reason="Origin not allowed")
        return

    await manager.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            # Handle ping/pong keep-alive
            if data == "ping":
                await manager.send_to(ws, {"type": "pong", "payload": {}})
            else:
                logger.debug("ws_message_received", data=data[:100])
    except WebSocketDisconnect:
        await manager.disconnect(ws)
