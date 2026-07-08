"""Phase 1.3: per-user WebSocket fan-out + the Redis pub/sub progress bus."""

import json
from unittest.mock import AsyncMock, MagicMock

from app.api.websocket.bus import publish_progress, user_channel
from app.api.websocket.events import ConnectionManager


def _ws() -> MagicMock:
    ws = MagicMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


class TestSendToUser:
    async def test_send_to_user_only_targets_that_user(self):
        m = ConnectionManager()
        a, b = _ws(), _ws()
        await m.connect(a, "userA")
        await m.connect(b, "userB")

        await m.send_to_user("userA", {"type": "x"})

        a.send_text.assert_awaited_once_with(json.dumps({"type": "x"}))
        b.send_text.assert_not_awaited()

    async def test_all_sockets_for_a_user_receive(self):
        m = ConnectionManager()
        a1, a2 = _ws(), _ws()
        await m.connect(a1, "userA")
        await m.connect(a2, "userA")

        await m.send_to_user("userA", {"type": "y"})

        a1.send_text.assert_awaited_once()
        a2.send_text.assert_awaited_once()

    async def test_disconnect_removes_from_user_bucket(self):
        m = ConnectionManager()
        a = _ws()
        await m.connect(a, "userA")
        assert m.active_count == 1
        await m.disconnect(a, "userA")
        assert m.active_count == 0


class TestBus:
    async def test_publish_progress_targets_user_channel(self):
        redis = AsyncMock()
        event = {"type": "application_progress", "payload": {"status": "applied"}}

        await publish_progress(redis, "userA", event)

        redis.publish.assert_awaited_once()
        channel, data = redis.publish.call_args.args
        assert channel == user_channel("userA")
        assert json.loads(data)["payload"]["status"] == "applied"
