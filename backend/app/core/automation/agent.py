"""Browser automation agent wrapping the browser-use package.

Provides a high-level ``BrowserAgent`` that delegates to the browser-use
``Agent`` for AI-driven web navigation, form filling, and data extraction.
"""

from __future__ import annotations

from typing import Any

import structlog
from pydantic import BaseModel

from app.config.settings import get_settings
from app.core.exceptions import BrowserError

logger = structlog.get_logger(__name__)


class BrowserAgent:
    """Wraps browser-use Agent for AI-driven browser navigation.

    Manages a single browser session with cookie persistence,
    configurable LLM, and structured output extraction.

    Args:
        task: Natural language description of what the agent should do.
        llm: LangChain-compatible LLM instance. Defaults to ChatOpenAI.
        sensitive_data: Credentials dict passed to browser-use
            (e.g. ``{"x_username": "...", "x_password": "..."}``).
        output_model: Pydantic model for structured output extraction.
    """

    def __init__(
        self,
        task: str,
        llm: Any | None = None,
        sensitive_data: dict[str, str] | None = None,
        output_model: type[BaseModel] | None = None,
    ) -> None:
        """Initialize a browser agent for a specific task.

        Args:
            task: Natural language description of what the agent should do.
            llm: LangChain-compatible LLM instance. Defaults to ChatOpenAI.
            sensitive_data: Credentials dict passed to browser-use.
            output_model: Pydantic model for structured output extraction.
        """
        self._settings = get_settings().browser
        self._task = task
        self._llm = llm
        self._sensitive_data = sensitive_data or {}
        self._output_model = output_model
        self._agent: Any | None = None
        self._browser: Any | None = None

    async def run(self) -> Any:
        """Execute the browser task and return results.

        Returns:
            Extracted data matching output_model, or raw result string.

        Raises:
            BrowserError: If browser-use is not installed or the task fails.
        """
        try:
            from browser_use import Agent, Browser, BrowserConfig
        except ImportError as exc:
            raise BrowserError(
                "browser-use package not installed. "
                "Install with: pip install browser-use"
            ) from exc

        browser_config = BrowserConfig(
            headless=self._settings.headless,
            chrome_instance_path=self._settings.user_data_dir,
        )
        self._browser = Browser(config=browser_config)

        llm = self._llm or self._get_default_llm()

        agent_kwargs: dict[str, Any] = {
            "task": self._task,
            "llm": llm,
            "browser": self._browser,
            "max_failures": self._settings.max_failures,
            "max_actions_per_step": 10,
        }
        if self._sensitive_data:
            agent_kwargs["sensitive_data"] = self._sensitive_data
        if self._output_model:
            agent_kwargs["generate_gif"] = False

        self._agent = Agent(**agent_kwargs)

        try:
            result = await self._agent.run(max_steps=self._settings.max_steps)
            logger.info(
                "browser_agent.completed",
                task=self._task[:80],
            )

            if self._output_model and hasattr(result, "model_output"):
                return result.model_output()
            return result

        except Exception as exc:
            logger.error(
                "browser_agent.failed",
                task=self._task[:80],
                error=str(exc),
            )
            raise BrowserError(str(exc)) from exc

        finally:
            if not self._settings.keep_alive and self._browser:
                await self._browser.close()

    def _get_default_llm(self) -> Any:
        """Create a default LangChain ChatOpenAI instance.

        Returns:
            ChatOpenAI configured from application settings.

        Raises:
            BrowserError: If langchain-openai is not installed.
        """
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise BrowserError(
                "langchain-openai package not installed. "
                "Install with: pip install langchain-openai"
            ) from exc

        settings = get_settings()
        return ChatOpenAI(
            model=settings.llm.default_model,
            api_key=settings.llm.openai_api_key.get_secret_value(),
            temperature=settings.llm.temperature,
        )

    async def close(self) -> None:
        """Close the browser session and release resources."""
        if self._browser:
            try:
                await self._browser.close()
            except Exception as exc:
                logger.warning("browser_agent.close_error", error=str(exc))
            finally:
                self._browser = None
                self._agent = None

    async def __aenter__(self) -> BrowserAgent:
        """Support async context manager usage."""
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Close browser on context exit."""
        await self.close()
