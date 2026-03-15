"""Analytics and dashboard service.

Provides aggregated statistics for the dashboard UI.
"""

import structlog
from sqlalchemy import String as SAString
from sqlalchemy import cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.constants import ApplicationStatus
from app.models.application import Application
from app.models.job import Job
from app.models.llm_usage import LLMUsage
from app.schemas.analytics import (
    ApplicationFunnelData,
    ATSScoreDistribution,
    DashboardStats,
    LLMUsageStats,
    TimelineEntry,
)

logger = structlog.get_logger(__name__)

_FUNNEL_STAGES = [
    ApplicationStatus.QUEUED,
    ApplicationStatus.PENDING_REVIEW,
    ApplicationStatus.APPROVED,
    ApplicationStatus.APPLYING,
    ApplicationStatus.APPLIED,
    ApplicationStatus.INTERVIEW,
    ApplicationStatus.OFFER,
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
]


async def get_dashboard_stats(db: AsyncSession) -> DashboardStats:
    """Compute top-level dashboard statistics.

    Args:
        db: Async database session.

    Returns:
        Aggregated dashboard stats.
    """
    total_jobs_result = await db.execute(select(func.count(Job.id)))
    total_jobs = total_jobs_result.scalar() or 0

    total_apps_result = await db.execute(select(func.count(Application.id)))
    total_apps = total_apps_result.scalar() or 0

    def _count_status(status: str):  # noqa: ANN202
        return select(func.count(Application.id)).where(
            Application.status == status,
        )

    pending = (await db.execute(_count_status(ApplicationStatus.PENDING_REVIEW))).scalar() or 0
    applied = (await db.execute(_count_status(ApplicationStatus.APPLIED))).scalar() or 0
    interview = (await db.execute(_count_status(ApplicationStatus.INTERVIEW))).scalar() or 0
    rejected = (await db.execute(_count_status(ApplicationStatus.REJECTED))).scalar() or 0
    offer = (await db.execute(_count_status(ApplicationStatus.OFFER))).scalar() or 0

    avg_ats_result = await db.execute(
        select(func.avg(Application.ats_score)).where(Application.ats_score.isnot(None)),
    )
    avg_ats = avg_ats_result.scalar() or 0.0

    llm_cost_result = await db.execute(
        select(func.coalesce(func.sum(LLMUsage.cost_usd), 0.0)),
    )
    total_llm_cost = llm_cost_result.scalar() or 0.0

    return DashboardStats(
        total_jobs_found=total_jobs,
        total_applications=total_apps,
        applications_pending=pending,
        applications_applied=applied,
        applications_interview=interview,
        applications_rejected=rejected,
        applications_offer=offer,
        avg_ats_score=round(float(avg_ats), 3),
        total_llm_cost_usd=round(float(total_llm_cost), 4),
    )


async def get_funnel(db: AsyncSession) -> list[ApplicationFunnelData]:
    """Get application funnel stage counts.

    Args:
        db: Async database session.

    Returns:
        List of funnel stage data.
    """
    result = await db.execute(
        select(Application.status, func.count(Application.id))
        .group_by(Application.status),
    )
    counts = {row[0]: row[1] for row in result.all()}

    return [
        ApplicationFunnelData(stage=stage, count=counts.get(stage, 0))
        for stage in _FUNNEL_STAGES
    ]


async def get_ats_distribution(db: AsyncSession) -> list[ATSScoreDistribution]:
    """Get ATS score distribution histogram.

    Args:
        db: Async database session.

    Returns:
        List of score range buckets.
    """
    ranges = [
        ("0-20", 0.0, 0.2),
        ("20-40", 0.2, 0.4),
        ("40-60", 0.4, 0.6),
        ("60-80", 0.6, 0.8),
        ("80-100", 0.8, 1.01),
    ]

    distribution: list[ATSScoreDistribution] = []
    for label, low, high in ranges:
        result = await db.execute(
            select(func.count(Application.id)).where(
                Application.ats_score >= low,
                Application.ats_score < high,
            ),
        )
        count = result.scalar() or 0
        distribution.append(ATSScoreDistribution(range_label=label, count=count))

    return distribution


async def get_llm_usage(db: AsyncSession) -> list[LLMUsageStats]:
    """Get LLM usage statistics grouped by provider + model.

    Args:
        db: Async database session.

    Returns:
        List of per-provider/model usage stats.
    """
    result = await db.execute(
        select(
            LLMUsage.provider,
            LLMUsage.model,
            func.count(LLMUsage.id).label("total_requests"),
            func.coalesce(func.sum(LLMUsage.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(LLMUsage.cost_usd), 0.0).label("total_cost"),
            func.coalesce(func.avg(LLMUsage.latency_ms), 0.0).label("avg_latency"),
        )
        .group_by(LLMUsage.provider, LLMUsage.model)
        .order_by(func.sum(LLMUsage.cost_usd).desc()),
    )

    return [
        LLMUsageStats(
            provider=row.provider,
            model=row.model,
            total_requests=row.total_requests,
            total_tokens=row.total_tokens,
            total_cost_usd=round(float(row.total_cost), 6),
            avg_latency_ms=round(float(row.avg_latency), 1),
        )
        for row in result.all()
    ]


async def get_timeline(db: AsyncSession) -> list[TimelineEntry]:
    """Get daily activity timeline for the last 30 days.

    Args:
        db: Async database session.

    Returns:
        Daily timeline entries.
    """
    # Applications created per day
    created_q = await db.execute(
        select(
            cast(Application.created_at, SAString).label("date"),
            func.count(Application.id).label("cnt"),
        )
        .group_by(cast(Application.created_at, SAString))
        .order_by(cast(Application.created_at, SAString).desc())
        .limit(30),
    )
    created_by_date = {
        str(r.date)[:10]: r.cnt for r in created_q.all()
    }

    # Applications applied per day
    applied_q = await db.execute(
        select(
            cast(Application.applied_at, SAString).label("date"),
            func.count(Application.id).label("cnt"),
        )
        .where(Application.applied_at.isnot(None))
        .group_by(cast(Application.applied_at, SAString))
        .order_by(cast(Application.applied_at, SAString).desc())
        .limit(30),
    )
    applied_by_date = {
        str(r.date)[:10]: r.cnt for r in applied_q.all()
    }

    # Jobs found per day
    jobs_q = await db.execute(
        select(
            cast(Job.created_at, SAString).label("date"),
            func.count(Job.id).label("cnt"),
        )
        .group_by(cast(Job.created_at, SAString))
        .order_by(cast(Job.created_at, SAString).desc())
        .limit(30),
    )
    jobs_by_date = {
        str(r.date)[:10]: r.cnt for r in jobs_q.all()
    }

    all_dates = sorted(
        set(created_by_date) | set(applied_by_date) | set(jobs_by_date),
        reverse=True,
    )[:30]

    return [
        TimelineEntry(
            date=d,
            applications_created=created_by_date.get(d, 0),
            applications_applied=applied_by_date.get(d, 0),
            jobs_found=jobs_by_date.get(d, 0),
        )
        for d in all_dates
    ]
