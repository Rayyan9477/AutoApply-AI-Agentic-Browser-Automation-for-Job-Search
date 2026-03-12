"""Application tracking API routes."""

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config.constants import DEFAULT_PAGE_SIZE
from app.schemas.application import (
    ApplicationBatchCreate,
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)
from app.services import application as app_service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=201,
    summary="Create an application",
)
async def create_application(
    data: ApplicationCreate,
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Create a single job application."""
    app = await app_service.create_application(db, data)
    return ApplicationResponse.model_validate(app)


@router.post(
    "/batch",
    response_model=list[ApplicationResponse],
    status_code=201,
    summary="Batch create applications",
)
async def batch_create(
    data: ApplicationBatchCreate,
    db: AsyncSession = Depends(get_db),
) -> list[ApplicationResponse]:
    """Create multiple job applications at once."""
    apps = await app_service.create_batch(db, data)
    return [ApplicationResponse.model_validate(a) for a in apps]


@router.get(
    "/",
    response_model=ApplicationListResponse,
    summary="List applications",
)
async def list_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=100),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> ApplicationListResponse:
    """List applications with pagination and optional status filter."""
    return await app_service.list_applications(db, page, page_size, status)


@router.get(
    "/{app_id}",
    response_model=ApplicationResponse,
    summary="Get a single application",
)
async def get_application(
    app_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Get a single application by ID. Returns 404 if not found."""
    app = await app_service.get_application(db, app_id)
    return ApplicationResponse.model_validate(app)


@router.put(
    "/{app_id}/approve",
    response_model=ApplicationResponse,
    summary="Approve a pending application",
)
async def approve_application(
    app_id: str,
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Approve a pending application for automated submission."""
    app = await app_service.approve_application(db, app_id)
    return ApplicationResponse.model_validate(app)


@router.put(
    "/{app_id}/status",
    response_model=ApplicationResponse,
    summary="Update application status",
)
async def update_status(
    app_id: str,
    update: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Update an application's status and optional notes."""
    app = await app_service.update_status(db, app_id, update)
    return ApplicationResponse.model_validate(app)
