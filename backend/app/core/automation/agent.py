"""Browser automation agent wrapping the browser-use package (0.11.5 API).

Provides a high-level ``BrowserAgent`` used by the board platforms (search, detail scraping,
login) that delegates to the browser-use ``Agent``. The browser profile and the LLM come from
the same runtime factory as the live apply path, so board search reasons with the configured
default model (Bedrock by default) instead of a hard-wired OpenAI/langchain client.
"""

from __future__ import annotations

import os
from typing import Any

import structlog
from pydantic import BaseModel

from app.config.settings import get_settings
from app.core.automation.runtime.factory import build_apply_llm, build_browser_profile
from app.core.automation.runtime.usage import record_agent_usage
from app.core.exceptions import BrowserError, LLMBudgetExceededError
from app.core.llm.budget import assert_within_budget

logger = structlog.get_logger(__name__)


def _default_llm() -> Any:
    """The runtime factory's model for ``settings.llm.default_model`` (no per-user key).

    A non-Bedrock model then authenticates only via ``OPENAI_API_KEY``; without it the first
    LLM call is certain to fail, so fail here, before a browser is launched and navigated.
    """
    model = get_settings().llm.default_model
    if not model.startswith("bedrock/") and not os.environ.get("OPENAI_API_KEY"):
        raise BrowserError(
            f"No credentials for browser model '{model}': set OPENAI_API_KEY "
            "or use a bedrock/ default model."
        )
    return build_apply_llm(None, model)


def _is_bedrock_model() -> bool:
    return get_settings().llm.default_model.startswith("bedrock/")


def _last_error(history: Any) -> str | None:
    """Most recent non-empty error recorded in a browser-use ``AgentHistoryList``."""
    errors = getattr(history, "errors", None)
    if not callable(errors):
        return None
    for error in reversed(errors() or []):
        if error:
            return str(error)
    return None


class BrowserAgent:
    """Wraps the browser-use ``Agent`` for AI-driven browser navigation.

    Each instance owns one ``BrowserSession`` built from a factory ``BrowserProfile``.

    Args:
        task: Natural language description of what the agent should do.
        llm: browser-use chat model. Defaults to the runtime factory's model for
            ``settings.llm.default_model``.
        sensitive_data: Credentials dict passed to browser-use
            (e.g. ``{"x_username": "...", "x_password": "..."}``).
        output_model: Pydantic model the agent's final answer must conform to.
        user_id: Owner of the run. When set, the monthly LLM budget is checked before a browser
            is launched and the run's token spend is recorded against it.
    """

    def __init__(
        self,
        task: str,
        llm: Any | None = None,
        sensitive_data: dict[str, str] | None = None,
        output_model: type[BaseModel] | None = None,
        user_id: str | None = None,
    ) -> None:
        self._settings = get_settings().browser
        self._task = task
        self._llm = llm
        self._sensitive_data = sensitive_data or {}
        self._output_model = output_model
        self._user_id = user_id
        self._agent: Any | None = None
        self._session: Any | None = None

    async def run(self) -> str | None:
        """Execute the browser task and return the agent's final result text.

        Returns:
            ``history.final_result()``: the agent's final answer (JSON text when the task asks
            for JSON, or the serialized ``output_model``), or ``None`` if it produced none.

        Raises:
            BrowserError: browser-use is unavailable, the run raised (browser/CDP, network,
                LLM auth), or the agent stopped with errors and no result. The original error
                message is preserved.
        """
        try:
            from browser_use import Agent, BrowserSession
        except ImportError as exc:
            raise BrowserError(f"browser-use is unavailable: {exc}") from exc

        if self._user_id:
            await assert_within_budget(self._user_id)  # before any browser is launched

        try:
            llm = self._llm or _default_llm()
            profile = build_browser_profile(headless=self._settings.headless)
            self._session = BrowserSession(browser_profile=profile)
            agent_kwargs: dict[str, Any] = {
                "browser_session": self._session,
                "max_failures": self._settings.max_failures,
                "step_timeout": self._settings.step_timeout,
            }
            if self._sensitive_data:
                agent_kwargs["sensitive_data"] = self._sensitive_data
            if self._output_model is not None:
                agent_kwargs["output_model_schema"] = self._output_model
            self._agent = Agent(task=self._task, llm=llm, **agent_kwargs)
            try:
                history = await self._agent.run(max_steps=self._settings.max_steps)
            finally:
                if self._user_id:
                    await record_agent_usage(
                        self._user_id,
                        self._agent,
                        provider="bedrock" if _is_bedrock_model() else "openai",
                    )
                # browser-use's Agent.run closes its own keep_alive=False session on every
                # exit path; drop our handle so close() doesn't kill it a second time.
                self._session = None
        except Exception as exc:
            logger.error("browser_agent.failed", task=self._task[:80], error=str(exc))
            if isinstance(exc, BrowserError | LLMBudgetExceededError):
                raise
            raise BrowserError(str(exc) or type(exc).__name__) from exc

        result = history.final_result()
        if result is None:
            error = _last_error(history)
            if error:
                logger.warning("browser_agent.no_result", task=self._task[:80], error=error)
                raise BrowserError(error)
        logger.info("browser_agent.completed", task=self._task[:80], has_result=result is not None)
        return result

    async def close(self) -> None:
        """Release a session that was built but never run (a completed run already closed it)."""
        session, self._session, self._agent = self._session, None, None
        if session is None:
            return
        try:
            await session.kill()
        except Exception as exc:
            logger.warning("browser_agent.close_error", error=str(exc))

    async def __aenter__(self) -> BrowserAgent:
        """Support async context manager usage."""
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Close browser on context exit."""
        await self.close()
