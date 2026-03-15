"""Unit tests for app.core.automation.session_manager.SessionManager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.core.automation.session_manager import SessionManager

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session_dir(tmp_path: Path) -> Path:
    d = tmp_path / "sessions"
    d.mkdir()
    return d


@pytest.fixture()
def manager(session_dir: Path) -> SessionManager:
    return SessionManager(session_dir=session_dir)


SAMPLE_COOKIES = [
    {"name": "session_id", "value": "abc123", "domain": ".example.com"},
    {"name": "csrf", "value": "xyz789", "domain": ".example.com"},
]


# ---------------------------------------------------------------------------
# save_cookies
# ---------------------------------------------------------------------------


class TestSaveCookies:
    async def test_save_creates_file(self, manager, session_dir):
        await manager.save_cookies("linkedin", SAMPLE_COOKIES)
        path = session_dir / "linkedin" / "cookies.json"
        assert path.exists()

    async def test_save_writes_valid_json(self, manager, session_dir):
        await manager.save_cookies("linkedin", SAMPLE_COOKIES)
        path = session_dir / "linkedin" / "cookies.json"
        data = json.loads(path.read_text())
        assert len(data) == 2
        assert data[0]["name"] == "session_id"


# ---------------------------------------------------------------------------
# load_cookies
# ---------------------------------------------------------------------------


class TestLoadCookies:
    async def test_load_returns_saved_cookies(self, manager):
        await manager.save_cookies("linkedin", SAMPLE_COOKIES)
        result = await manager.load_cookies("linkedin")
        assert result is not None
        assert len(result) == 2

    async def test_load_nonexistent_returns_none(self, manager):
        result = await manager.load_cookies("nonexistent")
        assert result is None

    async def test_load_corrupt_json_returns_none(self, manager, session_dir):
        path = session_dir / "linkedin" / "cookies.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json {{{{")
        result = await manager.load_cookies("linkedin")
        assert result is None


# ---------------------------------------------------------------------------
# clear_session
# ---------------------------------------------------------------------------


class TestClearSession:
    async def test_clear_removes_file(self, manager, session_dir):
        await manager.save_cookies("linkedin", SAMPLE_COOKIES)
        path = session_dir / "linkedin" / "cookies.json"
        assert path.exists()
        await manager.clear_session("linkedin")
        assert not path.exists()

    async def test_clear_nonexistent_does_not_raise(self, manager):
        # Should not raise
        await manager.clear_session("nonexistent")


# ---------------------------------------------------------------------------
# has_session
# ---------------------------------------------------------------------------


class TestHasSession:
    async def test_has_session_true_after_save(self, manager):
        await manager.save_cookies("linkedin", SAMPLE_COOKIES)
        assert await manager.has_session("linkedin") is True

    async def test_has_session_false_when_missing(self, manager):
        assert await manager.has_session("linkedin") is False

    async def test_has_session_false_after_clear(self, manager):
        await manager.save_cookies("linkedin", SAMPLE_COOKIES)
        await manager.clear_session("linkedin")
        assert await manager.has_session("linkedin") is False
