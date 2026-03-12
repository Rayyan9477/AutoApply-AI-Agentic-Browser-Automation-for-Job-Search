"""Job listing API routes."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config.constants import DEFAULT_PAGE_SIZE
from app.schemas.job import (
    JobAnalysisResponse,
    JobListingResponse,
    JobListResponse,
    JobSearchRequest,
)
from app.services import job_search as job_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/search",
    response_model=JobListResponse,
    summary="Search for jobs across platforms",
)
async def search_jobs(
    request: JobSearchRequest,
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """Launch a multi-platform job search.

    Platform scrapers are integrated in Phase 4.
    Currently returns empty results.
    """
    return await job_service.search_jobs(db, request)


@router.get(
    "/",
    response_model=JobListResponse,
    summary="List jobs with pagination",
)
async def list_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=100),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JobListResponse:
    """List stored job listings with optional status filter."""
    return await job_service.list_jobs(db, page, page_size, status)


@router.get(
    "/{job_id}",
    response_model=JobListingResponse,
    summary="Get a single job",
)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobListingResponse:
    """Get a single job listing by ID. Returns 404 if not found."""
    job = await job_service.get_job(db, job_id)
    return JobListingResponse.model_validate(job)


@router.post(
    "/{job_id}/analyze",
    response_model=JobAnalysisResponse,
    summary="Analyze job-candidate match",
)
async def analyze_job(
    job_id: str,
    resume_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> JobAnalysisResponse:
    """Analyze how well the candidate matches a job listing."""
    return await job_service.analyze_job(db, job_id, resume_id=resume_id)


@router.delete(
    "/{job_id}",
    status_code=204,
    summary="Delete a job",
)
async def delete_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a job listing and its associated applications."""
    await job_service.delete_job(db, job_id)
