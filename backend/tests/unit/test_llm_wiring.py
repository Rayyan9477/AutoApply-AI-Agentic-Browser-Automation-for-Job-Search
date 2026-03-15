"""Unit tests verifying LLM client wiring: initialization, completion calls,
cost tracking, fallback behaviour, and structured output parsing.

All litellm interactions are mocked with ``unittest.mock.AsyncMock``.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.core.exceptions import LLMProviderError, LLMRateLimitError, LLMTimeoutError
from app.core.llm.client import LLMClient, LLMResponse

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class AnalysisResult(BaseModel):
    """Sample Pydantic model for structured output tests."""
    summary: str
    confidence: float


def _build_mock_settings(
    fallback_providers: list[str] | None = None,
) -> MagicMock:
    """Return a mock Settings object matching LLM config shape."""
    settings = MagicMock()
    llm = MagicMock()
    llm.default_model = "openai/gpt-4o"
    llm.temperature = 0.7
    llm.max_tokens = 1024
    llm.fallback_providers = fallback_providers or []
    llm.portkey_api_key.get_secret_value.return_value = ""
    llm.openai_api_key.get_secret_value.return_value = "sk-test-key"
    llm.groq_api_key.get_secret_value.return_value = ""
    llm.gemini_api_key.get_secret_value.return_value = ""
    llm.openrouter_api_key.get_secret_value.return_value = ""
    settings.llm = llm
    return settings


def _build_completion_response(content: str = "ok") -> MagicMock:
    """Build a mock litellm ModelResponse."""
    response = MagicMock()
    choice = MagicMock()
    choice.message.content = content
    response.choices = [choice]
    usage = MagicMock()
    usage.prompt_tokens = 15
    usage.completion_tokens = 25
    usage.total_tokens = 40
    response.usage = usage
    return response


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLLMClientInitialization:
    async def test_llm_client_initializes_with_settings(self):
        """LLMClient should configure itself from the settings object."""
        mock_settings = _build_mock_settings(fallback_providers=["groq"])

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm"):
                client = LLMClient()

        # Verify internal state derived from settings
        assert client._llm.default_model == "openai/gpt-4o"
        assert client._llm.fallback_providers == ["groq"]

    async def test_llm_client_model_chain_includes_fallbacks(self):
        """_get_model_chain should include fallback providers."""
        mock_settings = _build_mock_settings(
            fallback_providers=["groq", "openrouter"],
        )

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm"):
                client = LLMClient()

        chain = client._get_model_chain(None)
        assert chain[0] == "openai/gpt-4o"
        assert "groq/gpt-4o" in chain
        assert "openrouter/gpt-4o" in chain


class TestLLMClientComplete:
    async def test_llm_client_complete_calls_litellm(self):
        """complete() should call litellm.acompletion with the correct args."""
        mock_settings = _build_mock_settings()
        mock_resp = _build_completion_response("Hello from LLM")

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm") as mock_litellm:
                mock_litellm.acompletion = AsyncMock(return_value=mock_resp)
                mock_litellm.completion_cost.return_value = 0.002
                mock_litellm.Usage = MagicMock

                client = LLMClient()
                result = await client.complete(
                    "Summarize this", system_prompt="You are helpful"
                )

        assert isinstance(result, LLMResponse)
        assert result.content == "Hello from LLM"
        assert result.model == "openai/gpt-4o"

        # Verify acompletion was called with the right messages
        call_kwargs = mock_litellm.acompletion.call_args.kwargs
        messages = call_kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "Summarize this"


class TestLLMClientCostTracking:
    async def test_llm_client_cost_tracking(self):
        """complete() should record cost from litellm.completion_cost."""
        mock_settings = _build_mock_settings()
        mock_resp = _build_completion_response("result")

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm") as mock_litellm:
                mock_litellm.acompletion = AsyncMock(return_value=mock_resp)
                mock_litellm.completion_cost.return_value = 0.0035
                mock_litellm.Usage = MagicMock

                client = LLMClient()
                result = await client.complete("test prompt")

        assert result.cost_usd == pytest.approx(0.0035)
        assert result.prompt_tokens == 15
        assert result.completion_tokens == 25
        assert result.total_tokens == 40
        mock_litellm.completion_cost.assert_called_once()


class TestLLMClientFallback:
    async def test_llm_client_fallback_on_provider_error(self):
        """When the primary provider raises APIError, the client should
        fall back to the next provider in the chain."""
        mock_settings = _build_mock_settings(fallback_providers=["groq"])
        mock_resp = _build_completion_response("fallback response")

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm") as mock_litellm:
                # Create real-ish exception types
                api_err = type("APIError", (Exception,), {})
                mock_litellm.APIError = api_err
                mock_litellm.RateLimitError = type("RateLimitError", (Exception,), {})
                mock_litellm.Timeout = type("Timeout", (Exception,), {})

                mock_litellm.acompletion = AsyncMock(
                    side_effect=[api_err("primary failed"), mock_resp],
                )
                mock_litellm.completion_cost.return_value = 0.001
                mock_litellm.Usage = MagicMock

                client = LLMClient()
                result = await client.complete("prompt")

        assert result.content == "fallback response"
        assert result.provider == "groq"
        assert mock_litellm.acompletion.call_count == 2

    async def test_llm_client_raises_rate_limit_when_all_exhausted(self):
        """When all providers hit rate limits, LLMRateLimitError is raised."""
        mock_settings = _build_mock_settings()

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm") as mock_litellm:
                rl_err = type("RateLimitError", (Exception,), {})
                mock_litellm.RateLimitError = rl_err
                mock_litellm.Timeout = type("Timeout", (Exception,), {})
                mock_litellm.APIError = type("APIError", (Exception,), {})
                mock_litellm.acompletion = AsyncMock(side_effect=rl_err("limit"))

                client = LLMClient()
                with pytest.raises(LLMRateLimitError):
                    await client.complete("prompt")

    async def test_llm_client_raises_timeout_when_all_exhausted(self):
        """When all providers time out, LLMTimeoutError is raised."""
        mock_settings = _build_mock_settings()

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm") as mock_litellm:
                timeout_err = type("Timeout", (Exception,), {})
                mock_litellm.Timeout = timeout_err
                mock_litellm.RateLimitError = type("RateLimitError", (Exception,), {})
                mock_litellm.APIError = type("APIError", (Exception,), {})
                mock_litellm.acompletion = AsyncMock(
                    side_effect=timeout_err("timed out"),
                )

                client = LLMClient()
                with pytest.raises(LLMTimeoutError):
                    await client.complete("prompt")


class TestLLMClientStructuredOutput:
    async def test_llm_client_structured_output_parses_json(self):
        """complete_with_structured_output should parse JSON into a Pydantic model."""
        mock_settings = _build_mock_settings()
        json_payload = json.dumps({"summary": "Great match", "confidence": 0.92})
        mock_resp = _build_completion_response(json_payload)

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm") as mock_litellm:
                mock_litellm.acompletion = AsyncMock(return_value=mock_resp)
                mock_litellm.completion_cost.return_value = 0.0
                mock_litellm.Usage = MagicMock

                client = LLMClient()
                result = await client.complete_with_structured_output(
                    "Analyze this job", AnalysisResult
                )

        assert isinstance(result, AnalysisResult)
        assert result.summary == "Great match"
        assert result.confidence == pytest.approx(0.92)

    async def test_llm_client_structured_output_raises_on_bad_json(self):
        """Malformed JSON should raise LLMProviderError."""
        mock_settings = _build_mock_settings()
        mock_resp = _build_completion_response("NOT JSON {{{")

        with patch("app.core.llm.client.get_settings", return_value=mock_settings):
            with patch("app.core.llm.client.litellm") as mock_litellm:
                mock_litellm.acompletion = AsyncMock(return_value=mock_resp)
                mock_litellm.completion_cost.return_value = 0.0
                mock_litellm.Usage = MagicMock

                client = LLMClient()
                with pytest.raises(LLMProviderError, match="Failed to parse"):
                    await client.complete_with_structured_output(
                        "prompt", AnalysisResult
                    )
