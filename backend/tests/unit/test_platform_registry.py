"""Unit tests for app.core.automation.platforms.registry.PlatformRegistry."""

from __future__ import annotations

import pytest

from app.core.automation.platforms.base import JobPlatform
from app.core.automation.platforms.registry import PlatformRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakePlatform(JobPlatform):
    """Concrete platform for testing the registry."""

    @property
    def name(self) -> str:
        return "fake"

    async def login(self, credentials):
        return True

    async def search(self, query, location="", filters=None):
        return []

    async def scrape_details(self, job_url):
        return None

    async def apply(self, job, resume_path, cover_letter_path=None):
        return True


class AnotherPlatform(JobPlatform):
    @property
    def name(self) -> str:
        return "another"

    async def login(self, credentials):
        return True

    async def search(self, query, location="", filters=None):
        return []

    async def scrape_details(self, job_url):
        return None

    async def apply(self, job, resume_path, cover_letter_path=None):
        return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def registry() -> PlatformRegistry:
    return PlatformRegistry()


class TestRegister:
    def test_register_platform(self, registry):
        registry.register("fake", FakePlatform)
        assert registry.has("fake") is True

    def test_register_overwrites_existing(self, registry):
        registry.register("fake", FakePlatform)
        registry.register("fake", AnotherPlatform)
        assert registry.get("fake") is AnotherPlatform


class TestGet:
    def test_get_returns_class(self, registry):
        registry.register("fake", FakePlatform)
        assert registry.get("fake") is FakePlatform

    def test_get_nonexistent_returns_none(self, registry):
        assert registry.get("nonexistent") is None


class TestHas:
    def test_has_true_for_registered(self, registry):
        registry.register("fake", FakePlatform)
        assert registry.has("fake") is True

    def test_has_false_for_unregistered(self, registry):
        assert registry.has("unknown") is False


class TestListPlatforms:
    def test_list_empty(self, registry):
        assert registry.list_platforms() == []

    def test_list_registered(self, registry):
        registry.register("fake", FakePlatform)
        registry.register("another", AnotherPlatform)
        names = registry.list_platforms()
        assert "fake" in names
        assert "another" in names


class TestCreate:
    def test_create_returns_instance(self, registry):
        registry.register("fake", FakePlatform)
        instance = registry.create("fake")
        assert isinstance(instance, FakePlatform)

    def test_create_nonexistent_raises_key_error(self, registry):
        with pytest.raises(KeyError, match="not registered"):
            registry.create("nonexistent")

    def test_create_shows_available_in_error(self, registry):
        registry.register("fake", FakePlatform)
        with pytest.raises(KeyError, match="fake"):
            registry.create("missing")
