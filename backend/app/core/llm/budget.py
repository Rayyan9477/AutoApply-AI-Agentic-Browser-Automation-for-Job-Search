"""Per-user monthly LLM budget: month-to-date spend, enforcement and status.

The window is the UTC calendar month. The cap is SOFT: it is checked before a call or run
starts, so one in-flight call (or run) may overshoot it. The check fails OPEN on infrastructure
errors: a database blip must not take down every LLM feature, and the next call re-checks.
``LLM__USER_MONTHLY_BUDGET_USD <= 0`` disables enforcement.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.exceptions import LLMBudgetExceededError
from app.models.llm_usage import LLMUsage

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class BudgetStatus:
    """A user's budget standing. ``remaining_usd`` is None when enforcement is disabled."""

    limit_usd: float
    spent_usd: float
    remaining_usd: float | None
    resets_at: datetime  # naive UTC, first of next month


def month_start_utc(now: datetime | None = None) -> datetime:
    """First instant of the UTC calendar month, as a NAIVE datetime (the DB convention)."""
    now = now or datetime.now(UTC)
    if now.tzinfo is not None:
        now = now.astimezone(UTC)
    return datetime(now.year, now.month, 1)


def next_month_start_utc(now: datetime | None = None) -> datetime:
    """First instant of the NEXT UTC calendar month (naive): when the budget resets."""
    start = month_start_utc(now)
    return datetime(start.year + (start.month == 12), start.month % 12 + 1, 1)


async def month_to_date_spend(db: AsyncSession, user_id: str) -> float:
    """SUM(cost_usd) of ``user_id`` LLM usage this UTC month (explicit user, no tenant)."""
    total = (
        await db.execute(
            select(func.coalesce(func.sum(LLMUsage.cost_usd), 0.0))
            .where(LLMUsage.user_id == user_id, LLMUsage.created_at >= month_start_utc())
            .execution_options(skip_tenant_filter=True)
        )
    ).scalar()
    return float(total or 0.0)


async def assert_within_budget(user_id: str, db: AsyncSession | None = None) -> None:
    """Raise :class:`LLMBudgetExceededError` when the user's month-to-date spend hit the cap.

    Opens its own short session when ``db`` is None. Fails open on any other error.
    """
    limit = get_settings().llm.user_monthly_budget_usd
    if limit <= 0:
        return
    try:
        if db is not None:
            # SAVEPOINT: a failed SELECT must not leave the caller's transaction aborted
            # (PostgreSQL rejects every later statement until rollback).
            async with db.begin_nested():
                spent = await month_to_date_spend(db, user_id)
        else:
            from app.db.session import async_session_factory

            async with async_session_factory() as session:
                spent = await month_to_date_spend(session, user_id)
    except Exception as exc:
        logger.warning("llm_budget_check_failed", user_id=user_id, error=str(exc))
        return
    if spent >= limit:
        raise LLMBudgetExceededError(spent_usd=spent, limit_usd=limit)


async def budget_status(db: AsyncSession, user_id: str) -> BudgetStatus:
    """The user's month-to-date spend against the configured cap."""
    limit = get_settings().llm.user_monthly_budget_usd
    spent = await month_to_date_spend(db, user_id)
    return BudgetStatus(
        limit_usd=limit,
        spent_usd=spent,
        remaining_usd=max(0.0, limit - spent) if limit > 0 else None,
        resets_at=next_month_start_utc(),
    )
