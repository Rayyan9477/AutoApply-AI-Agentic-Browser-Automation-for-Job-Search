"""build_apply_llm routes bedrock/<id> models through AWS Bedrock (no api_key)."""

from __future__ import annotations

from app.core.automation.runtime.factory import build_apply_llm


def test_bedrock_model_returns_bedrock_chat_without_api_key() -> None:
    llm = build_apply_llm(None, "bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0")
    assert type(llm).__name__ == "ChatAnthropicBedrock"
    # The bedrock model id is stripped of the ``bedrock/`` routing prefix.
    assert getattr(llm, "model", "").startswith("anthropic.claude")


def test_non_bedrock_model_uses_openai_byo_key() -> None:
    llm = build_apply_llm("sk-test", "gpt-4o")
    assert type(llm).__name__ == "ChatOpenAI"
