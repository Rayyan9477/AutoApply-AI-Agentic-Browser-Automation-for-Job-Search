"""Analytics and dashboard API routes."""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.analytics import (
    ApplicationFunnelData,
    ATSScoreDistribution,
    DashboardStats,
    LLMUsageStats,
    TimelineEntry,
)
from app.services import analytics as analytics_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get(
    "/dashboard",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
)
async def dashboard(
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """Get aggregated dashboard statistics."""
    return await analytics_service.get_dashboard_stats(db)


@router.get(
    "/funnel",
    response_model=list[ApplicationFunnelData],
    summary="Get application funnel",
)
async def funnel(
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationFunnelData]:
    """Get application funnel stage counts."""
    return await analytics_service.get_funnel(db)


@router.get(
    "/ats-scores",
    response_model=list[ATSScoreDistribution],
    summary="Get ATS score distribution",
)
async def ats_scores(
    db: AsyncSession = Depends(get_db),
) -> list[ATSScoreDistribution]:
    """Get ATS score distribution histogram."""
    return await analytics_service.get_ats_distribution(db)


@router.get(
    "/llm-usage",
    response_model=list[LLMUsageStats],
    summary="Get LLM usage stats",
)
async def llm_usage(
    db: AsyncSession = Depends(get_db),
) -> list[LLMUsageStats]:
    """Get LLM provider usage statistics."""
    return await analytics_service.get_llm_usage(db)


@router.get(
    "/timeline",
    response_model=list[TimelineEntry],
    summary="Get daily activity timeline",
)
async def timeline(
    db: AsyncSession = Depends(get_db),
) -> list[TimelineEntry]:
    """Get daily activity timeline entries."""
    return await analytics_service.get_timeline(db)
