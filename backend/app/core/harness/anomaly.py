"""System-wide anomaly detection.

Beyond individual apply runs, the harness watches workflow/system health and records
``SystemIssue`` rows (surfaced on an admin/health view). Rule-based and global (not
tenant-scoped), so application counts bypass the tenant filter.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.harness import SystemIssue

logger = structlog.get_logger(__name__)

MIN_SAMPLE = 5
FAILED_RATE_THRESHOLD = 0.5
QUEUE_DEPTH_THRESHOLD = 100
RECENT_WINDOW_HOURS = 6  # only count applications from the recent window (not all-time)
_ARQ_QUEUE = "arq:queue"


def _issue(
    category: str, severity: str, signals: dict[str, Any], diagnosis: str, now: datetime
) -> SystemIssue:
    return SystemIssue(
        category=category,
        severity=severity,
        signals=signals,
        diagnosis=diagnosis,
        detected_at=now,
        status="open",
    )


async def _upsert_issue(
    db: AsyncSession,
    *,
    category: str,
    severity: str,
    signals: dict[str, Any],
    diagnosis: str,
    now: datetime,
) -> SystemIssue:
    """Refresh the existing OPEN issue of this category, or open a new one.

    Prevents the detector (which runs every 15 min) from re-inserting an identical row on every
    tick for a single ongoing condition — the table would otherwise grow without bound.
    """
    existing = (
        await db.execute(
            select(SystemIssue).where(
                SystemIssue.category == category, SystemIssue.status == "open"
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        existing.severity = severity
        existing.signals = signals
        existing.diagnosis = diagnosis
        existing.detected_at = now
        return existing
    issue = _issue(category, severity, signals, diagnosis, now)
    db.add(issue)
    return issue


async def detect_anomalies(
    db: AsyncSession, *, redis: Any | None = None, now: datetime | None = None
) -> list[SystemIssue]:
    """Inspect workflow health and persist any detected ``SystemIssue`` rows."""
    now = now or datetime.now(UTC)
    # Compare against the naive-UTC column (created_at is DateTime without tz); deriving a naive
    # bound keeps the window correct on both SQLite and Postgres.
    naive_now = now.replace(tzinfo=None) if now.tzinfo else now
    window_start = naive_now - timedelta(hours=RECENT_WINDOW_HOURS)
    issues: list[SystemIssue] = []

    # 1. High RECENT application-failure rate (global; bypass the tenant filter). Windowed so an
    #    acute outage fires even on a mature deploy, and old failures age out after they recover.
    total = (
        await db.execute(
            select(func.count(Application.id))
            .where(Application.created_at >= window_start)
            .execution_options(skip_tenant_filter=True)
        )
    ).scalar() or 0
    failed = (
        await db.execute(
            select(func.count(Application.id))
            .where(
                Application.status == ApplicationStatus.FAILED,
                Application.created_at >= window_start,
            )
            .execution_options(skip_tenant_filter=True)
        )
    ).scalar() or 0
    if total >= MIN_SAMPLE and failed / total >= FAILED_RATE_THRESHOLD:
        issues.append(
            await _upsert_issue(
                db,
                category="apply_failure_rate",
                severity="critical",
                signals={"total": total, "failed": failed, "window_hours": RECENT_WINDOW_HOURS},
                diagnosis=f"{failed}/{total} apps FAILED in the last {RECENT_WINDOW_HOURS}h",
                now=now,
            )
        )

    # 2. Queue backlog.
    if redis is not None:
        try:
            depth = await redis.llen(_ARQ_QUEUE)
        except Exception:
            depth = 0
        if depth and depth > QUEUE_DEPTH_THRESHOLD:
            issues.append(
                await _upsert_issue(
                    db,
                    category="queue_depth",
                    severity="warning",
                    signals={"depth": depth},
                    diagnosis=f"Queue backlog: {depth}",
                    now=now,
                )
            )

    if issues:
        await db.commit()
        for issue in issues:
            await db.refresh(issue)
        logger.info("anomaly.detected", count=len(issues))
    return issues
