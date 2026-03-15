"""Unit tests for the WebSocket ConnectionManager (app.api.websocket.events).

Uses ``unittest.mock.AsyncMock`` to simulate WebSocket objects.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

from app.api.websocket.events import ConnectionManager

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_ws() -> MagicMock:
    """Create a mock WebSocket with async accept/send_text methods."""
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConnectionManagerConnect:
    async def test_connection_manager_connect_accepts_websocket(self):
        """connect() should call ws.accept() and track the connection."""
        manager = ConnectionManager()
        ws = _make_mock_ws()

        await manager.connect(ws)

        ws.accept.assert_awaited_once()
        assert manager.active_count == 1

    async def test_connection_manager_connect_multiple(self):
        """Multiple connections should all be tracked."""
        manager = ConnectionManager()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()

        await manager.connect(ws1)
        await manager.connect(ws2)

        assert manager.active_count == 2


class TestConnectionManagerDisconnect:
    async def test_connection_manager_disconnect_removes_connection(self):
        """disconnect() should remove the WebSocket from active list."""
        manager = ConnectionManager()
        ws = _make_mock_ws()

        await manager.connect(ws)
        assert manager.active_count == 1

        await manager.disconnect(ws)
        assert manager.active_count == 0

    async def test_connection_manager_disconnect_idempotent(self):
        """Disconnecting a WebSocket that is not tracked should not raise."""
        manager = ConnectionManager()
        ws = _make_mock_ws()

        # Should not raise even though ws was never connected
        await manager.disconnect(ws)
        assert manager.active_count == 0


class TestConnectionManagerBroadcast:
    async def test_connection_manager_broadcast_sends_to_all(self):
        """broadcast() should send the JSON message to every connected client."""
        manager = ConnectionManager()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()

        await manager.connect(ws1)
        await manager.connect(ws2)

        message = {"type": "update", "data": "hello"}
        await manager.broadcast(message)

        expected_payload = json.dumps(message)
        ws1.send_text.assert_awaited_once_with(expected_payload)
        ws2.send_text.assert_awaited_once_with(expected_payload)

    async def test_connection_manager_broadcast_removes_stale(self):
        """If a WebSocket raises on send, it should be removed as stale."""
        manager = ConnectionManager()
        ws_good = _make_mock_ws()
        ws_stale = _make_mock_ws()
        ws_stale.send_text = AsyncMock(side_effect=RuntimeError("connection closed"))

        await manager.connect(ws_good)
        await manager.connect(ws_stale)
        assert manager.active_count == 2

        await manager.broadcast({"type": "ping"})

        # Stale connection should have been removed
        assert manager.active_count == 1
        ws_good.send_text.assert_awaited_once()

    async def test_connection_manager_broadcast_empty_connections(self):
        """Broadcasting with no connections should be a no-op."""
        manager = ConnectionManager()
        # Should not raise
        await manager.broadcast({"type": "test"})
        assert manager.active_count == 0


class TestConnectionManagerSendTo:
    async def test_send_to_specific_client(self):
        """send_to() should only send to the specified WebSocket."""
        manager = ConnectionManager()
        ws1 = _make_mock_ws()
        ws2 = _make_mock_ws()

        await manager.connect(ws1)
        await manager.connect(ws2)

        message = {"type": "direct"}
        await manager.send_to(ws1, message)

        ws1.send_text.assert_awaited_once_with(json.dumps(message))
        ws2.send_text.assert_not_awaited()

    async def test_send_to_removes_on_error(self):
        """If send_to fails, the WebSocket should be disconnected."""
        manager = ConnectionManager()
        ws = _make_mock_ws()
        ws.send_text = AsyncMock(side_effect=RuntimeError("closed"))

        await manager.connect(ws)
        assert manager.active_count == 1

        await manager.send_to(ws, {"type": "fail"})
        assert manager.active_count == 0
