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
        """Create a LangChain-compatible LLM based on the preferred provider.

        Falls back through: OpenAI → DeepSeek (OpenAI-compatible) → Groq.

        Returns:
            LangChain chat model instance configured from application settings.

        Raises:
            BrowserError: If no suitable LLM package is installed.
        """
        settings = get_settings()
        llm_config = settings.llm
        preferred = llm_config.preferred_provider

        openai_key = llm_config.openai_api_key.get_secret_value()
        deepseek_key = llm_config.deepseek_api_key.get_secret_value()
        groq_key = llm_config.groq_api_key.get_secret_value()

        # Try preferred provider in order
        if preferred == "deepseek" and deepseek_key:
            return self._build_chat_openai(
                model=llm_config.default_model if "deepseek" in llm_config.default_model.lower() else "deepseek-chat",
                api_key=deepseek_key,
                base_url="https://api.deepseek.com/v1",
            )

        if preferred != "deepseek" and openai_key:
            return self._build_chat_openai(
                model=llm_config.default_model,
                api_key=openai_key,
            )

        # Fallback: DeepSeek via OpenAI-compatible
        if deepseek_key:
            return self._build_chat_openai(
                model="deepseek-chat",
                api_key=deepseek_key,
                base_url="https://api.deepseek.com/v1",
            )

        # Fallback: Groq
        if groq_key:
            try:
                from langchain_groq import ChatGroq
            except ImportError as exc:
                raise BrowserError(
                    "langchain-groq not installed. Install with: pip install langchain-groq"
                ) from exc
            return ChatGroq(
                model="llama-3.1-70b-versatile",
                api_key=groq_key,
                temperature=llm_config.temperature,
            )

        raise BrowserError(
            "No LLM provider configured. Set at least OPENAI_API_KEY, "
            "DEEPSEEK_API_KEY, or GROQ_API_KEY in your .env file."
        )

    def _build_chat_openai(
        self, model: str, api_key: str, base_url: str | None = None,
    ) -> Any:
        """Create a ChatOpenAI instance, optionally with a custom base URL.

        This works for both OpenAI and OpenAI-compatible providers like DeepSeek.
        """
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise BrowserError(
                "langchain-openai package not installed. "
                "Install with: pip install langchain-openai"
            ) from exc

        kwargs: dict[str, Any] = {
            "model": model,
            "api_key": api_key,
            "temperature": get_settings().llm.temperature,
        }
        if base_url:
            kwargs["base_url"] = base_url

        return ChatOpenAI(**kwargs)

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
