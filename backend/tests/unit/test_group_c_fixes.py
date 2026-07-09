"""Group C remediation regression tests: WS send serialization, skill version-race retry,
refresh-cookie Secure flag, redis pool cleanup on failed ping."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Response
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError

from app.config.settings import Environment

# --- C2: WebSocket per-socket send serialization ----------------------------


class TestWebSocketSendLock:
    async def test_sends_serialize_per_socket(self):
        from app.api.websocket.events import ConnectionManager

        mgr = ConnectionManager()
        ws = MagicMock()
        ws.accept = AsyncMock()
        state = {"depth": 0, "max": 0}

        async def fake_send(_payload):
            state["depth"] += 1
            state["max"] = max(state["max"], state["depth"])
            await asyncio.sleep(0.005)
            state["depth"] -= 1

        ws.send_text = fake_send
        await mgr.connect(ws, "u1")

        await asyncio.gather(*[mgr.send_to_user("u1", {"n": i}) for i in range(5)])

        assert state["max"] == 1  # the per-connection lock serialized concurrent sends


# --- C3: record_skill retries on a version collision ------------------------


class TestSkillVersionRace:
    async def test_retries_on_integrity_error(self, db_session, monkeypatch):
        from app.core.harness.skills import record_skill

        await record_skill(db_session, "race", "first skill")  # version 1 (real commit)

        real_commit = db_session.commit
        calls = {"n": 0}

        async def flaky_commit():
            calls["n"] += 1
            if calls["n"] == 1:
                raise IntegrityError("INSERT", {}, Exception("uq_domain_skill_version"))
            await real_commit()

        monkeypatch.setattr(db_session, "commit", flaky_commit)
        skill = await record_skill(db_session, "race", "second skill")

        assert skill is not None and skill.version == 2
        assert calls["n"] == 2  # retried after the simulated collision


# --- C4: refresh cookie Secure flag -----------------------------------------


class TestRefreshCookieSecure:
    def _cookie_header(self, env: Environment) -> str:
        from app.api.v1 import auth

        fake = MagicMock()
        fake.environment = env
        fake.auth.refresh_token_expire_days = 30
        resp = Response()
        with patch.object(auth, "get_settings", return_value=fake):
            auth._set_refresh_cookie(resp, "raw-token")
        return resp.headers.get("set-cookie", "")

    def test_secure_in_staging(self):
        assert "Secure" in self._cookie_header(Environment.STAGING)

    def test_secure_in_production(self):
        assert "Secure" in self._cookie_header(Environment.PRODUCTION)

    def test_not_secure_in_development(self):
        assert "Secure" not in self._cookie_header(Environment.DEVELOPMENT)


# --- C5: redis pool cleanup on failed ping ----------------------------------


class TestRedisPoolCleanup:
    async def test_closes_half_open_pool_on_failed_ping(self):
        import app.db.redis as r

        fake_pool = MagicMock()
        fake_pool.disconnect = AsyncMock()
        fake_client = MagicMock()
        fake_client.ping = AsyncMock(side_effect=RedisError("down"))
        fake_client.aclose = AsyncMock()

        with patch.object(r, "ConnectionPool") as cp, patch.object(
            r, "Redis", return_value=fake_client
        ):
            cp.from_url.return_value = fake_pool
            await r.init_redis_pool("redis://localhost:6379/0")

        fake_client.aclose.assert_awaited_once()
        fake_pool.disconnect.assert_awaited_once()
        assert r.get_redis() is None
