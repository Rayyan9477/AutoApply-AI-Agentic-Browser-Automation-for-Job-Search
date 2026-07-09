"""F6: authentication flow, WebSocket ticket, and the rate limiter."""

import fakeredis.aioredis
import pytest

from app.core import ratelimit
from app.core.exceptions import RateLimitError

API = "/api/v1/auth"
CREDS = {"email": "u@x.com", "password": "password123"}
FORM = {"username": "u@x.com", "password": "password123"}


class TestAuthFlow:
    async def test_register_login_me(self, anon_client):
        r = await anon_client.post(f"{API}/register", json=CREDS)
        assert r.status_code == 201, r.text
        assert r.json()["email"] == "u@x.com"

        r = await anon_client.post(f"{API}/login", data=FORM)
        assert r.status_code == 200, r.text
        token = r.json()["access_token"]

        r = await anon_client.get(f"{API}/me", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["email"] == "u@x.com"

    async def test_ws_ticket_issued_for_authed_user(self, anon_client):
        await anon_client.post(f"{API}/register", json=CREDS)
        token = (await anon_client.post(f"{API}/login", data=FORM)).json()["access_token"]
        r = await anon_client.get(f"{API}/ws-ticket", headers={"Authorization": f"Bearer {token}"})
        assert r.status_code == 200
        assert r.json()["ticket"]

    async def test_duplicate_email_returns_409(self, anon_client):
        await anon_client.post(f"{API}/register", json=CREDS)
        r = await anon_client.post(f"{API}/register", json=CREDS)
        assert r.status_code == 409

    async def test_wrong_password_returns_401(self, anon_client):
        await anon_client.post(f"{API}/register", json=CREDS)
        r = await anon_client.post(f"{API}/login", data={"username": "u@x.com", "password": "nope"})
        assert r.status_code == 401

    async def test_bad_token_returns_401(self, anon_client):
        r = await anon_client.get(f"{API}/me", headers={"Authorization": "Bearer garbage"})
        assert r.status_code == 401


class TestRouterGuard:
    async def test_unauthenticated_request_rejected(self, anon_client):
        r = await anon_client.get("/api/v1/applications/")
        assert r.status_code == 401

    async def test_ws_ticket_requires_auth(self, anon_client):
        r = await anon_client.get(f"{API}/ws-ticket")
        assert r.status_code == 401


class TestRateLimiter:
    async def test_blocks_after_limit(self, monkeypatch):
        fake = fakeredis.aioredis.FakeRedis()
        monkeypatch.setattr(ratelimit, "get_redis", lambda: fake)
        limiter = ratelimit.RateLimiter()

        for _ in range(3):
            await limiter.check("client:/auth/login", limit=3, window=60)
        with pytest.raises(RateLimitError):
            await limiter.check("client:/auth/login", limit=3, window=60)


class TestRefreshFlow:
    async def _register_and_login(self, client):
        await client.post(f"{API}/register", json=CREDS)
        await client.post(f"{API}/login", data=FORM)

    async def test_refresh_rotates_and_returns_token(self, anon_client):
        await self._register_and_login(anon_client)
        r = await anon_client.post(f"{API}/refresh")
        assert r.status_code == 200, r.text
        assert r.json()["access_token"]

    async def test_refresh_without_cookie_401(self, anon_client):
        r = await anon_client.post(f"{API}/refresh")
        assert r.status_code == 401

    async def test_reuse_detection_revokes_family(self, anon_client):
        await self._register_and_login(anon_client)
        old = anon_client.cookies.get("refresh_token")
        assert old

        # First rotation succeeds; the old token is now retired.
        assert (await anon_client.post(f"{API}/refresh")).status_code == 200

        # Replaying the retired token triggers reuse-detection -> 401 + family revoked.
        anon_client.cookies.clear()
        r2 = await anon_client.post(f"{API}/refresh", cookies={"refresh_token": old})
        assert r2.status_code == 401

    async def test_logout_revokes_refresh(self, anon_client):
        await self._register_and_login(anon_client)
        assert (await anon_client.post(f"{API}/logout")).status_code == 204
        # The rotated cookie was cleared and the family revoked.
        r = await anon_client.post(f"{API}/refresh")
        assert r.status_code == 401
