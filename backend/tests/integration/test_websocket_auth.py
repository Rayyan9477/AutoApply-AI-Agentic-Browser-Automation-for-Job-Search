"""WebSocket ticket authentication (verifies reject-before-accept actually rejects)."""

from contextlib import asynccontextmanager

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app.core.security import create_ws_ticket
from app.main import create_app


def _client() -> TestClient:
    app = create_app()

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    app.router.lifespan_context = _noop_lifespan
    return TestClient(app)


def test_ws_rejects_without_ticket():
    with pytest.raises(WebSocketDisconnect):
        with _client().websocket_connect("/ws") as ws:
            ws.receive_text()


def test_ws_rejects_bad_ticket():
    with pytest.raises(WebSocketDisconnect):
        with _client().websocket_connect("/ws?ticket=garbage") as ws:
            ws.receive_text()


def test_ws_accepts_valid_ticket():
    ticket = create_ws_ticket("someuser0000000000000000000000aa")
    with _client().websocket_connect(f"/ws?ticket={ticket}") as ws:
        ws.send_text("ping")
        assert ws.receive_json() == {"type": "pong", "payload": {}}
