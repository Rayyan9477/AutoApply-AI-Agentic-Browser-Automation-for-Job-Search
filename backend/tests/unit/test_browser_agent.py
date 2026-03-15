"""Unit tests for app.core.automation.agent.BrowserAgent."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import BrowserError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_agent(task="search jobs", llm=None):
    """Create a BrowserAgent with mocked settings."""
    mock_browser_settings = MagicMock()
    mock_browser_settings.headless = True
    mock_browser_settings.user_data_dir = ""
    mock_browser_settings.max_failures = 3
    mock_browser_settings.max_steps = 50
    mock_browser_settings.keep_alive = False

    mock_settings = MagicMock()
    mock_settings.browser = mock_browser_settings

    with patch("app.core.automation.agent.get_settings", return_value=mock_settings):
        from app.core.automation.agent import BrowserAgent
        agent = BrowserAgent(task=task, llm=llm, sensitive_data={"user": "test"})
    return agent


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


class TestBrowserAgentInit:
    def test_creates_agent_with_task(self):
        agent = _make_agent(task="apply to jobs")
        assert agent._task == "apply to jobs"

    def test_stores_sensitive_data(self):
        agent = _make_agent()
        assert agent._sensitive_data == {"user": "test"}


# ---------------------------------------------------------------------------
# run — import error
# ---------------------------------------------------------------------------


class TestBrowserAgentRun:
    async def test_run_raises_browser_error_when_no_browser_use(self):
        agent = _make_agent()
        with patch.dict("sys.modules", {"browser_use": None}):
            with pytest.raises(BrowserError, match="browser-use"):
                await agent.run()


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestBrowserAgentClose:
    async def test_close_when_no_browser(self):
        agent = _make_agent()
        # Should not raise
        await agent.close()
        assert agent._browser is None

    async def test_close_with_browser(self):
        agent = _make_agent()
        mock_browser = AsyncMock()
        agent._browser = mock_browser
        await agent.close()
        mock_browser.close.assert_awaited_once()
        assert agent._browser is None
        assert agent._agent is None

    async def test_close_handles_exception(self):
        agent = _make_agent()
        mock_browser = AsyncMock()
        mock_browser.close.side_effect = RuntimeError("close failed")
        agent._browser = mock_browser
        # Should not raise, just warn
        await agent.close()
        assert agent._browser is None


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestBrowserAgentContextManager:
    async def test_async_context_manager(self):
        agent = _make_agent()
        async with agent as a:
            assert a is agent
        # After exit, close should have been called
        assert agent._browser is None

    async def test_context_manager_closes_browser(self):
        agent = _make_agent()
        mock_browser = AsyncMock()
        agent._browser = mock_browser
        async with agent:
            pass
        mock_browser.close.assert_awaited_once()


# ---------------------------------------------------------------------------
# _get_default_llm
# ---------------------------------------------------------------------------


class TestGetDefaultLLM:
    def test_raises_browser_error_when_no_langchain(self):
        agent = _make_agent()
        with patch.dict("sys.modules", {"langchain_openai": None}):
            with pytest.raises(BrowserError, match="langchain-openai"):
                agent._get_default_llm()
