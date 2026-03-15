"""Unit tests for app.db.redis — connection pool management."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db import redis as redis_mod

# ---------------------------------------------------------------------------
# Fixtures — reset module-level globals between tests
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_redis_globals():
    """Ensure module globals are clean before and after each test."""
    redis_mod._redis_pool = None
    redis_mod._redis_client = None
    yield
    redis_mod._redis_pool = None
    redis_mod._redis_client = None


# ---------------------------------------------------------------------------
# get_redis
# ---------------------------------------------------------------------------


class TestGetRedis:
    def test_returns_none_when_not_initialized(self):
        assert redis_mod.get_redis() is None

    def test_returns_client_when_set(self):
        mock_client = MagicMock()
        redis_mod._redis_client = mock_client
        assert redis_mod.get_redis() is mock_client


# ---------------------------------------------------------------------------
# is_redis_available
# ---------------------------------------------------------------------------


class TestIsRedisAvailable:
    async def test_returns_false_when_no_client(self):
        result = await redis_mod.is_redis_available()
        assert result is False

    async def test_returns_true_on_successful_ping(self):
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        redis_mod._redis_client = mock_client
        result = await redis_mod.is_redis_available()
        assert result is True

    async def test_returns_false_on_ping_failure(self):
        from redis.exceptions import RedisError

        mock_client = AsyncMock()
        mock_client.ping.side_effect = RedisError("connection refused")
        redis_mod._redis_client = mock_client
        result = await redis_mod.is_redis_available()
        assert result is False


# ---------------------------------------------------------------------------
# init_redis_pool
# ---------------------------------------------------------------------------


class TestInitRedisPool:
    async def test_successful_init_sets_globals(self):
        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping.return_value = True

        with patch("app.db.redis.ConnectionPool.from_url", return_value=mock_pool):
            with patch("app.db.redis.Redis", return_value=mock_client):
                await redis_mod.init_redis_pool("redis://localhost:6379/0")

        assert redis_mod._redis_pool is mock_pool
        assert redis_mod._redis_client is mock_client

    async def test_failed_init_clears_globals(self):
        from redis.exceptions import RedisError

        mock_pool = MagicMock()
        mock_client = AsyncMock()
        mock_client.ping.side_effect = RedisError("fail")

        with patch("app.db.redis.ConnectionPool.from_url", return_value=mock_pool):
            with patch("app.db.redis.Redis", return_value=mock_client):
                await redis_mod.init_redis_pool("redis://localhost:6379/0")

        assert redis_mod._redis_pool is None
        assert redis_mod._redis_client is None


# ---------------------------------------------------------------------------
# close_redis_pool
# ---------------------------------------------------------------------------


class TestCloseRedisPool:
    async def test_close_clears_globals(self):
        mock_client = AsyncMock()
        mock_pool = AsyncMock()
        redis_mod._redis_client = mock_client
        redis_mod._redis_pool = mock_pool

        await redis_mod.close_redis_pool()

        assert redis_mod._redis_client is None
        assert redis_mod._redis_pool is None
        mock_client.close.assert_awaited_once()
        mock_pool.disconnect.assert_awaited_once()

    async def test_close_when_not_initialized(self):
        # Should not raise
        await redis_mod.close_redis_pool()
