"""Job listing API routes."""

from typing import Any

import structlog
from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_redis, get_tenant_db
from app.config.constants import DEFAULT_PAGE_SIZE
from app.core.ratelimit import rate_limit
from app.db.arq import get_arq_pool
from app.schemas.job import (
    JobAnalysisResponse,
    JobListingResponse,
    JobListResponse,
    JobSearchRequest,
    JobSearchResponse,
)
from app.services import job_search as job_service
from app.services.dispatch import get_search_status

logger = structlog.get_logger(__name__)
router = APIRouter()

# Job search fans out to browser automation / Exa — cap per-client rate.
_COSTLY = Depends(rate_limit(30, 60))


@router.post(
    "/search",
    response_model=JobSearchResponse,
    dependencies=[_COSTLY],
    summary="Search for jobs across platforms",
)
async def search_jobs(
    request: JobSearchRequest,
    user: CurrentUser,
    db: AsyncSession = Depends(get_tenant_db),
    pool: ArqRedis | None = Depends(get_arq_pool),
) -> JobSearchResponse:
    """Launch a multi-platform job search for the current user.

    Exa results come back inline. Board searches run in the background when a worker is up
    (``search_id`` + ``pending_boards``; progress over the WebSocket and
    ``GET /jobs/search/{search_id}``), otherwise inline as before.
    """
    return await job_service.search_jobs(db, request, user.id, pool)


@router.get("/search/{search_id}", summary="Status of a background board search")
async def get_search_status_route(
    search_id: str,
    user: CurrentUser,
    redis: Redis | None = Depends(get_redis),
) -> dict[str, Any]:
    """Per-board status of a search; 404 if unknown, expired, not yours, or Redis is down."""
    status = await get_search_status(redis, user.id, search_id) if redis is not None else None
    if status is None:
        raise HTTPException(status_code=404, detail="Search not found")
    return status


@router.get("/", response_model=JobListResponse, summary="List jobs with pagination")
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=100),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
) -> JobListResponse:
    """List the current user's stored job listings with optional status filter."""
    return await job_service.list_jobs(db, page, page_size, status)


@router.get("/{job_id}", response_model=JobListingResponse, summary="Get a single job")
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_tenant_db),
) -> JobListingResponse:
    """Get one of the current user's job listings by ID. Returns 404 if not found."""
    job = await job_service.get_job(db, job_id)
    return JobListingResponse.model_validate(job)


@router.post(
    "/{job_id}/analyze", response_model=JobAnalysisResponse, summary="Analyze job-candidate match"
)
async def analyze_job(
    job_id: str,
    resume_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
) -> JobAnalysisResponse:
    """Analyze how well the candidate matches a job listing."""
    return await job_service.analyze_job(db, job_id, resume_id=resume_id)


@router.delete("/{job_id}", status_code=204, summary="Delete a job")
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    """Delete one of the current user's job listings and its applications."""
    await job_service.delete_job(db, job_id)
