"""Persist LLM usage records to the database for cost tracking."""

from __future__ import annotations

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm.client import LLMResponse
from app.models.llm_usage import LLMUsage

logger = structlog.get_logger(__name__)


async def record_usage(
    db: AsyncSession,
    response: LLMResponse,
    purpose: str = "general",
    trace_id: str | None = None,
) -> None:
    """Save an LLM call record to the database.

    Args:
        db: Async database session.
        response: LLMResponse from LLMClient.complete().
        purpose: Label for what the call was used for.
        trace_id: Optional distributed trace ID.
    """
    record = LLMUsage(
        provider=response.provider,
        model=response.model,
        prompt_tokens=response.prompt_tokens,
        completion_tokens=response.completion_tokens,
        total_tokens=response.total_tokens,
        cost_usd=response.cost_usd,
        latency_ms=int(response.latency_ms),
        purpose=purpose,
        trace_id=trace_id,
    )
    db.add(record)
    await db.commit()
    logger.debug(
        "llm_usage_recorded",
        provider=response.provider,
        model=response.model,
        tokens=response.total_tokens,
        cost=round(response.cost_usd, 6),
        purpose=purpose,
    )
