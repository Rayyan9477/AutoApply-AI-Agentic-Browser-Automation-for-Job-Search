"""browser-use runtime factory (browser-use 0.11.5).

Builds a per-tenant ``BrowserProfile`` (session hydration + identity + domain scoping)
and an apply ``Agent`` with reliability config and typed output.

NOTE: constructing a ``BrowserProfile`` is pure config (no browser launched). Actually
*running* the agent requires a real (headful / Xvfb) browser environment, a valid
platform ``storage_state`` (from an assisted login), and a configured LLM key — that
end-to-end path is exercised in a real-browser spike, not in CI.
"""

from __future__ import annotations

from typing import Any

from app.config.settings import get_settings
from app.core.automation.runtime.result import ApplicationResult


def build_browser_profile(
    *,
    storage_state: dict[str, Any] | None = None,
    proxy: Any | None = None,
    user_agent: str | None = None,
    allowed_domains: list[str] | None = None,
    headless: bool | None = None,
) -> Any:
    """Construct a per-tenant ``BrowserProfile`` (hydrated session + stable identity)."""
    from browser_use import BrowserProfile

    settings = get_settings().browser
    return BrowserProfile(
        storage_state=storage_state,
        proxy=proxy,
        user_agent=user_agent,
        allowed_domains=allowed_domains,
        headless=settings.headless if headless is None else headless,
        keep_alive=False,
    )


def build_apply_llm(api_key: str | None, model: str = "gpt-4o") -> Any:
    """Build the browser-use LLM the agent reasons with.

    A ``bedrock/<model-id>`` model routes through AWS Bedrock, authenticated via the standard
    AWS credential chain (env / ~/.aws / instance role) — no api_key. Any other model uses the
    per-user BYO key via ``ChatOpenAI``.
    """
    if model.startswith("bedrock/"):
        from browser_use.llm import ChatAnthropicBedrock

        return ChatAnthropicBedrock(
            model=model.split("/", 1)[1],
            aws_region=get_settings().llm.bedrock_region,
        )
    from browser_use import ChatOpenAI

    return ChatOpenAI(model=model, api_key=api_key)


def build_apply_agent(
    task: str,
    *,
    llm: Any,
    profile: Any,
    tools: Any | None = None,
    extend_system_message: str = "",
) -> Any:
    """Build the apply ``Agent`` with the typed ``ApplicationResult`` output schema."""
    from browser_use import Agent, BrowserSession

    settings = get_settings().browser
    session = BrowserSession(browser_profile=profile)
    return Agent(
        task=task,
        llm=llm,
        browser_session=session,
        tools=tools,
        output_model_schema=ApplicationResult,
        max_failures=settings.max_failures,
        extend_system_message=extend_system_message,
    )
