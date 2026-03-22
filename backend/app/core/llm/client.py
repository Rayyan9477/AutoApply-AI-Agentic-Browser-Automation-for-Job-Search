"""Unified LLM client with Portkey gateway and LiteLLM provider abstraction."""

from __future__ import annotations

import json
import time
from typing import Any

import litellm
import structlog
from pydantic import BaseModel, ConfigDict

from app.config.settings import get_settings
from app.core.exceptions import LLMProviderError, LLMRateLimitError, LLMTimeoutError
from app.observability.metrics import (
    llm_cost_usd,
    llm_latency_seconds,
    llm_requests_total,
    llm_tokens_total,
)

logger = structlog.get_logger(__name__)


class LLMResponse(BaseModel):
    """Structured response from an LLM completion call."""

    model_config = ConfigDict(frozen=True)

    content: str
    model: str
    provider: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0


class LLMClient:
    """Unified async LLM client with provider fallback and cost tracking.

    Wraps LiteLLM's ``acompletion`` with Portkey gateway headers,
    automatic fallback through configured providers, and Prometheus
    metrics recording for every call.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._llm = settings.llm
        self._configure_portkey()
        self._configure_api_keys()

    def _configure_portkey(self) -> None:
        """Configure Portkey gateway headers if API key is available."""
        portkey_key = self._llm.portkey_api_key.get_secret_value()
        if portkey_key:
            litellm.set_verbose = False
            litellm.success_callback = ["portkey"]
            litellm.failure_callback = ["portkey"]
            # Portkey headers are passed via metadata per-request
            logger.info("portkey_gateway_configured")

    def _configure_api_keys(self) -> None:
        """Push provider API keys into litellm's key registry."""
        key_map: dict[str, str] = {
            "openai_api_key": self._llm.openai_api_key.get_secret_value(),
            "groq_api_key": self._llm.groq_api_key.get_secret_value(),
            "gemini_api_key": self._llm.gemini_api_key.get_secret_value(),
            "openrouter_api_key": self._llm.openrouter_api_key.get_secret_value(),
        }
        for attr, value in key_map.items():
            if value:
                setattr(litellm, attr, value)

    def _build_messages(
        self, prompt: str, system_prompt: str
    ) -> list[dict[str, str]]:
        """Build the messages list for a chat completion request."""
        messages: list[dict[str, str]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _get_model_chain(self, model: str | None) -> list[str]:
        """Return the ordered list of models to try (primary + fallbacks)."""
        primary = model or self._llm.default_model
        fallbacks = [
            f"{provider}/{primary.split('/')[-1]}"
            for provider in self._llm.fallback_providers
        ]
        return [primary, *fallbacks]

    def _portkey_metadata(self) -> dict[str, Any]:
        """Build Portkey metadata dict for request tracing."""
        portkey_key = self._llm.portkey_api_key.get_secret_value()
        if not portkey_key:
            return {}
        return {
            "portkey_api_key": portkey_key,
        }

    async def complete(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        purpose: str = "general",
    ) -> LLMResponse:
        """Send completion request with fallback chain and metrics.

        Uses ``litellm.acompletion()`` under the hood. Falls back through
        configured providers on failure. Records Prometheus metrics.

        Args:
            prompt: The user prompt text.
            system_prompt: Optional system prompt prepended to messages.
            model: Override model identifier (e.g. ``gpt-4o``).
            temperature: Sampling temperature override.
            max_tokens: Max completion tokens override.
            response_format: JSON mode / structured output spec.
            purpose: Label for metrics (e.g. ``cover_letter``).

        Returns:
            Populated ``LLMResponse`` with content and usage metadata.

        Raises:
            LLMRateLimitError: Provider rate limit hit on all attempts.
            LLMTimeoutError: All providers timed out.
            LLMProviderError: Non-recoverable provider failure.
        """
        messages = self._build_messages(prompt, system_prompt)
        temp = temperature if temperature is not None else self._llm.temperature
        tokens = max_tokens if max_tokens is not None else self._llm.max_tokens
        model_chain = self._get_model_chain(model)
        metadata = self._portkey_metadata()
        last_error: Exception | None = None

        for attempt_model in model_chain:
            provider = attempt_model.split("/")[0] if "/" in attempt_model else "openai"
            start = time.perf_counter()
            try:
                kwargs: dict[str, Any] = {
                    "model": attempt_model,
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": tokens,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                if metadata:
                    kwargs["metadata"] = metadata

                response = await litellm.acompletion(**kwargs)
                latency_s = time.perf_counter() - start
                elapsed_ms = latency_s * 1000

                usage = response.usage or litellm.Usage()
                cost = litellm.completion_cost(completion_response=response)

                self._record_metrics(
                    provider=provider,
                    model=attempt_model,
                    purpose=purpose,
                    status="success",
                    latency_s=latency_s,
                    prompt_tokens=usage.prompt_tokens or 0,
                    completion_tokens=usage.completion_tokens or 0,
                    cost=cost,
                )

                content = response.choices[0].message.content or ""
                logger.info(
                    "llm_completion_success",
                    model=attempt_model,
                    tokens=usage.total_tokens,
                    cost_usd=round(cost, 6),
                    latency_ms=round(elapsed_ms, 1),
                )
                return LLMResponse(
                    content=content,
                    model=attempt_model,
                    provider=provider,
                    prompt_tokens=usage.prompt_tokens or 0,
                    completion_tokens=usage.completion_tokens or 0,
                    total_tokens=usage.total_tokens or 0,
                    cost_usd=cost,
                    latency_ms=elapsed_ms,
                )

            except litellm.RateLimitError as exc:
                last_error = exc
                self._record_metrics(
                    provider=provider,
                    model=attempt_model,
                    purpose=purpose,
                    status="rate_limited",
                    latency_s=(time.perf_counter() - start),
                )
                logger.warning(
                    "llm_rate_limited", model=attempt_model, error=str(exc)
                )
                continue

            except litellm.Timeout as exc:
                last_error = exc
                self._record_metrics(
                    provider=provider,
                    model=attempt_model,
                    purpose=purpose,
                    status="timeout",
                    latency_s=(time.perf_counter() - start),
                )
                logger.warning(
                    "llm_timeout", model=attempt_model, error=str(exc)
                )
                continue

            except litellm.APIError as exc:
                last_error = exc
                self._record_metrics(
                    provider=provider,
                    model=attempt_model,
                    purpose=purpose,
                    status="error",
                    latency_s=(time.perf_counter() - start),
                )
                logger.error(
                    "llm_api_error", model=attempt_model, error=str(exc)
                )
                continue

        # All models exhausted — raise the appropriate typed error
        if isinstance(last_error, litellm.RateLimitError):
            raise LLMRateLimitError(provider=model_chain[-1])
        if isinstance(last_error, litellm.Timeout):
            raise LLMTimeoutError(f"All models timed out: {model_chain}")
        raise LLMProviderError(
            provider=model_chain[-1],
            message=str(last_error) if last_error else "Unknown error",
        )

    async def complete_with_structured_output(
        self,
        prompt: str,
        output_schema: type[BaseModel],
        system_prompt: str = "",
        model: str | None = None,
        purpose: str = "structured",
    ) -> BaseModel:
        """Get structured JSON output parsed into a Pydantic model.

        Args:
            prompt: The user prompt text.
            output_schema: Pydantic model class for response validation.
            system_prompt: Optional system prompt.
            model: Override model identifier.
            purpose: Label for metrics.

        Returns:
            Instance of ``output_schema`` populated from the LLM response.

        Raises:
            LLMProviderError: If JSON parsing or validation fails.
        """
        schema = output_schema.model_json_schema()
        augmented_system = (
            f"{system_prompt}\n\n"
            "You MUST respond with valid JSON matching this schema:\n"
            f"```json\n{json.dumps(schema, indent=2)}\n```\n"
            "Respond ONLY with the JSON object, no extra text."
        ).strip()

        response = await self.complete(
            prompt=prompt,
            system_prompt=augmented_system,
            model=model,
            response_format={"type": "json_object"},
            purpose=purpose,
        )

        try:
            data = json.loads(response.content)
            return output_schema.model_validate(data)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "structured_output_parse_failed",
                content=response.content[:500],
                error=str(exc),
            )
            raise LLMProviderError(
                provider=response.provider,
                message=f"Failed to parse structured output: {exc}",
            ) from exc

    def _record_metrics(
        self,
        *,
        provider: str,
        model: str,
        purpose: str,
        status: str,
        latency_s: float,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        cost: float = 0.0,
    ) -> None:
        """Record Prometheus metrics for an LLM call."""
        llm_requests_total.labels(
            provider=provider, model=model, status=status
        ).inc()
        llm_latency_seconds.labels(
            provider=provider, model=model, purpose=purpose
        ).observe(latency_s)
        if prompt_tokens:
            llm_tokens_total.labels(
                provider=provider, model=model, direction="prompt"
            ).inc(prompt_tokens)
        if completion_tokens:
            llm_tokens_total.labels(
                provider=provider, model=model, direction="completion"
            ).inc(completion_tokens)
        if cost > 0:
            llm_cost_usd.labels(provider=provider, model=model).inc(cost)
