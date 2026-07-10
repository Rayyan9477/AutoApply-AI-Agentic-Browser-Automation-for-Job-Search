"""Application tracking API routes."""

import structlog
from arq.connections import ArqRedis
from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_redis, get_tenant_db
from app.config.constants import DEFAULT_PAGE_SIZE
from app.core.automation.intervention import resolve_intervention
from app.db.arq import get_arq_pool
from app.schemas.application import (
    ApplicationBatchCreate,
    ApplicationBulkApprove,
    ApplicationCreate,
    ApplicationIntervention,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
    CoverLetterResponse,
)
from app.services import application as app_service
from app.services import cover_letter as cover_letter_service
from app.services import dispatch

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/", response_model=ApplicationResponse, status_code=201, summary="Create an application"
)
async def create_application(
    data: ApplicationCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_tenant_db),
    pool: ArqRedis | None = Depends(get_arq_pool),
) -> ApplicationResponse:
    """Create a single job application and dispatch it according to apply_mode."""
    app = await app_service.create_application(db, data, user.id)
    await dispatch.dispatch_for_mode(db, pool, app)
    return app_service.application_to_response(app)


@router.post(
    "/batch",
    response_model=list[ApplicationResponse],
    status_code=201,
    summary="Batch create applications",
)
async def batch_create(
    data: ApplicationBatchCreate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_tenant_db),
    pool: ArqRedis | None = Depends(get_arq_pool),
) -> list[ApplicationResponse]:
    """Create multiple job applications at once, each dispatched by apply_mode."""
    apps = await app_service.create_batch(db, data, user.id)
    for app in apps:
        await dispatch.dispatch_for_mode(db, pool, app)
    return [app_service.application_to_response(a) for a in apps]


@router.get("/", response_model=ApplicationListResponse, summary="List applications")
async def list_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=DEFAULT_PAGE_SIZE, ge=1, le=100),
    status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_tenant_db),
) -> ApplicationListResponse:
    """List the current user's applications with pagination and optional status filter."""
    return await app_service.list_applications(db, page, page_size, status)


@router.post(
    "/bulk-approve",
    response_model=dict,
    summary="Approve and enqueue a set of staged (batch) applications",
)
async def bulk_approve(
    data: ApplicationBulkApprove,
    db: AsyncSession = Depends(get_tenant_db),
    pool: ArqRedis | None = Depends(get_arq_pool),
) -> dict:
    """Approve a set of the current user's staged applications and enqueue them together."""
    count = await dispatch.bulk_approve(db, pool, data.application_ids)
    return {"approved": count}


@router.get("/{app_id}", response_model=ApplicationResponse, summary="Get a single application")
async def get_application(
    app_id: str,
    db: AsyncSession = Depends(get_tenant_db),
) -> ApplicationResponse:
    """Get one of the current user's applications by ID. Returns 404 if not found."""
    app = await app_service.get_application(db, app_id)
    return app_service.application_to_response(app)


@router.put(
    "/{app_id}/approve",
    response_model=ApplicationResponse,
    summary="Approve a pending application",
)
async def approve_application(
    app_id: str,
    db: AsyncSession = Depends(get_tenant_db),
    pool: ArqRedis | None = Depends(get_arq_pool),
) -> ApplicationResponse:
    """Approve a pending application and enqueue it for automated submission."""
    app = await app_service.approve_application(db, app_id)
    await dispatch.enqueue_apply(pool, app.id)
    return app_service.application_to_response(app)


@router.post(
    "/{app_id}/cover-letter",
    response_model=CoverLetterResponse,
    summary="Generate a cover letter for an application",
)
async def generate_cover_letter(
    app_id: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_tenant_db),
) -> CoverLetterResponse:
    """Generate (LLM) and store a cover letter for the application's job + resume."""
    app = await cover_letter_service.generate_cover_letter(db, app_id, user.id)
    return CoverLetterResponse(application_id=app.id, cover_letter_path=app.cover_letter_path)


@router.post(
    "/{app_id}/intervention",
    response_model=dict,
    summary="Resolve a pending CAPTCHA/2FA intervention",
)
async def resolve_application_intervention(
    app_id: str,
    data: ApplicationIntervention,
    db: AsyncSession = Depends(get_tenant_db),
    redis: Redis | None = Depends(get_redis),
) -> dict:
    """Deliver the user's response to a worker waiting on a CAPTCHA/2FA challenge."""
    await app_service.get_application(db, app_id)  # 404 + tenant-ownership check
    if redis is None:
        return {"resolved": False, "detail": "intervention channel unavailable"}
    await resolve_intervention(redis, app_id, data.response)
    return {"resolved": True}


@router.put(
    "/{app_id}/status",
    response_model=ApplicationResponse,
    summary="Update application status",
)
async def update_status(
    app_id: str,
    update: ApplicationStatusUpdate,
    db: AsyncSession = Depends(get_tenant_db),
) -> ApplicationResponse:
    """Update an application's status and optional notes."""
    app = await app_service.update_status(db, app_id, update)
    return app_service.application_to_response(app)
