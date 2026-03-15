"""Unit tests for app.core.llm.client.LLMClient."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.core.exceptions import LLMProviderError, LLMRateLimitError
from app.core.llm.client import LLMClient, LLMResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class SampleOutput(BaseModel):
    """Pydantic model for structured output tests."""
    title: str
    score: float


def _make_settings_mock() -> MagicMock:
    """Build a mock settings object matching the LLM config shape."""
    settings = MagicMock()
    llm = MagicMock()
    llm.default_model = "openai/gpt-4o"
    llm.temperature = 0.7
    llm.max_tokens = 1024
    llm.fallback_providers = []
    llm.portkey_api_key.get_secret_value.return_value = ""
    llm.openai_api_key.get_secret_value.return_value = "sk-test"
    llm.groq_api_key.get_secret_value.return_value = ""
    llm.gemini_api_key.get_secret_value.return_value = ""
    llm.openrouter_api_key.get_secret_value.return_value = ""
    settings.llm = llm
    return settings


def _make_completion_response(content: str = "Hello world") -> MagicMock:
    """Build a mock litellm completion response."""
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = content
    usage = MagicMock()
    usage.prompt_tokens = 10
    usage.completion_tokens = 20
    usage.total_tokens = 30
    response.usage = usage
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client() -> LLMClient:
    with patch("app.core.llm.client.get_settings", return_value=_make_settings_mock()):
        with patch("app.core.llm.client.litellm"):
            return LLMClient()


# ---------------------------------------------------------------------------
# complete - success
# ---------------------------------------------------------------------------


class TestCompleteSuccess:
    async def test_complete_returns_llm_response(self, client: LLMClient) -> None:
        mock_response = _make_completion_response("Generated text")

        with patch("app.core.llm.client.litellm") as mock_litellm:
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)
            mock_litellm.completion_cost.return_value = 0.001
            mock_litellm.Usage = MagicMock
            result = await client.complete("Write something")

        assert isinstance(result, LLMResponse)
        assert result.content == "Generated text"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 20

    async def test_complete_uses_default_model(self, client: LLMClient) -> None:
        mock_response = _make_completion_response()

        with patch("app.core.llm.client.litellm") as mock_litellm:
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)
            mock_litellm.completion_cost.return_value = 0.0
            mock_litellm.Usage = MagicMock
            result = await client.complete("prompt")

        assert result.model == "openai/gpt-4o"


# ---------------------------------------------------------------------------
# complete - fallback on error
# ---------------------------------------------------------------------------


class TestCompleteFallback:
    async def test_complete_falls_back_on_api_error(self, client: LLMClient) -> None:
        mock_response = _make_completion_response("fallback result")

        with patch("app.core.llm.client.litellm") as mock_litellm:
            api_error = type("APIError", (Exception,), {})
            mock_litellm.APIError = api_error
            mock_litellm.RateLimitError = type("RateLimitError", (Exception,), {})
            mock_litellm.Timeout = type("Timeout", (Exception,), {})

            # First call fails, configure fallback
            client._llm.fallback_providers = ["groq"]
            mock_litellm.acompletion = AsyncMock(
                side_effect=[api_error("fail"), mock_response]
            )
            mock_litellm.completion_cost.return_value = 0.0
            mock_litellm.Usage = MagicMock

            result = await client.complete("prompt")

        assert result.content == "fallback result"


# ---------------------------------------------------------------------------
# complete - rate limit
# ---------------------------------------------------------------------------


class TestCompleteRateLimit:
    async def test_complete_raises_rate_limit_error(self, client: LLMClient) -> None:
        with patch("app.core.llm.client.litellm") as mock_litellm:
            rate_error = type("RateLimitError", (Exception,), {})
            mock_litellm.RateLimitError = rate_error
            mock_litellm.Timeout = type("Timeout", (Exception,), {})
            mock_litellm.APIError = type("APIError", (Exception,), {})
            mock_litellm.acompletion = AsyncMock(side_effect=rate_error("limit"))

            with pytest.raises(LLMRateLimitError):
                await client.complete("prompt")


# ---------------------------------------------------------------------------
# complete_with_structured_output
# ---------------------------------------------------------------------------


class TestStructuredOutput:
    async def test_parses_json_into_pydantic_model(self, client: LLMClient) -> None:
        json_content = json.dumps({"title": "Engineer", "score": 0.95})
        mock_response = _make_completion_response(json_content)

        with patch("app.core.llm.client.litellm") as mock_litellm:
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)
            mock_litellm.completion_cost.return_value = 0.0
            mock_litellm.Usage = MagicMock

            result = await client.complete_with_structured_output(
                "prompt", SampleOutput
            )

        assert isinstance(result, SampleOutput)
        assert result.title == "Engineer"
        assert result.score == pytest.approx(0.95)

    async def test_raises_provider_error_on_invalid_json(self, client: LLMClient) -> None:
        mock_response = _make_completion_response("not valid json {{{")

        with patch("app.core.llm.client.litellm") as mock_litellm:
            mock_litellm.acompletion = AsyncMock(return_value=mock_response)
            mock_litellm.completion_cost.return_value = 0.0
            mock_litellm.Usage = MagicMock

            with pytest.raises(LLMProviderError, match="Failed to parse"):
                await client.complete_with_structured_output("prompt", SampleOutput)
