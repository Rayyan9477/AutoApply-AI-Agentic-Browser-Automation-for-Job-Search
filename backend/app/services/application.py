"""Application management service.

Handles creating, listing, approving, and updating job applications.
"""

from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError as DBIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.core.exceptions import RecordNotFoundError
from app.models.application import Application
from app.models.enums import ApplicationStatus
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.application import (
    ApplicationBatchCreate,
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationStatusUpdate,
)

logger = structlog.get_logger(__name__)


def application_to_response(app: Application) -> ApplicationResponse:
    """Serialize an Application, hydrating job_title/company from the related job.

    The denormalized display fields are only filled when the ``job`` relationship is already
    loaded (list/detail eager-load it); callers that pass an object without it loaded — e.g.
    a freshly created row — get ``None``, and never trigger a lazy load in the async context.
    """
    item = ApplicationResponse.model_validate(app)
    if "job" not in sa_inspect(app).unloaded and app.job is not None:
        item.job_title = app.job.title
        item.company = app.job.company
    return item

# States that DON'T block a fresh application for the same (user, job) — mirrors the
# partial-unique ``uq_app_active_job`` index.
_TERMINAL_STATES = (
    ApplicationStatus.REJECTED,
    ApplicationStatus.WITHDRAWN,
    ApplicationStatus.FAILED,
)


async def _assert_owned(db: AsyncSession, model: Any, record_id: str) -> None:
    """Confirm a referenced record exists for the current tenant before linking to it.

    The ``do_orm_execute`` filter is SELECT-only, so it never validates FK targets on
    INSERT — without this a client could create an Application referencing another
    tenant's job_id/resume_id. The scoped SELECT returns None for a foreign id.
    """
    found = (
        await db.execute(select(model.id).where(model.id == record_id))
    ).scalar_one_or_none()
    if found is None:
        raise RecordNotFoundError(f"{model.__name__} '{record_id}' not found")


async def create_application(
    db: AsyncSession,
    data: ApplicationCreate,
    user_id: str,
) -> Application:
    """Create a single job application.

    Args:
        db: Async database session.
        data: Application creation data.

    Returns:
        The newly created Application.
    """
    await _assert_owned(db, Job, data.job_id)
    if data.resume_id:
        await _assert_owned(db, Resume, data.resume_id)

    application = Application(
        user_id=user_id,
        job_id=data.job_id,
        resume_id=data.resume_id,
        apply_mode=data.apply_mode,
        status=ApplicationStatus.QUEUED,
    )
    # Attempt the insert inside a SAVEPOINT so a unique-constraint violation rolls back
    # ONLY this insert (not the whole session) — the caller then continues to commit.
    try:
        async with db.begin_nested():
            db.add(application)
            await db.flush()
    except DBIntegrityError:
        # An active application for this (user, job) already exists — return it (idempotent
        # create), so a double-submit/retry can't create a duplicate auto-apply.
        existing = (
            await db.execute(
                select(Application).where(
                    Application.job_id == data.job_id,
                    Application.status.notin_(_TERMINAL_STATES),
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            logger.info("application_create_idempotent", app_id=existing.id, job_id=data.job_id)
            return existing
        raise
    await db.commit()
    await db.refresh(application)
    logger.info("application_created", app_id=application.id, job_id=data.job_id)
    return application


async def create_batch(
    db: AsyncSession,
    data: ApplicationBatchCreate,
    user_id: str,
) -> list[Application]:
    """Create multiple applications at once.

    Args:
        db: Async database session.
        data: Batch creation data containing multiple job IDs.

    Returns:
        List of newly created Applications.
    """
    if data.resume_id:
        await _assert_owned(db, Resume, data.resume_id)
    requested = set(data.job_ids)
    owned = set(
        (await db.execute(select(Job.id).where(Job.id.in_(requested)))).scalars().all()
    )
    missing = requested - owned
    if missing:
        raise RecordNotFoundError(f"Jobs not found: {sorted(missing)}")

    # Skip jobs that already have an active application (dedup, mirrors uq_app_active_job).
    existing_active = set(
        (
            await db.execute(
                select(Application.job_id).where(
                    Application.job_id.in_(requested),
                    Application.status.notin_(_TERMINAL_STATES),
                )
            )
        ).scalars().all()
    )

    applications: list[Application] = []
    for job_id in data.job_ids:
        if job_id in existing_active:
            continue
        app = Application(
            user_id=user_id,
            job_id=job_id,
            resume_id=data.resume_id,
            apply_mode=data.apply_mode,
            status=ApplicationStatus.QUEUED,
        )
        db.add(app)
        applications.append(app)

    await db.commit()
    for app in applications:
        await db.refresh(app)

    logger.info("batch_applications_created", count=len(applications))
    return applications


async def list_applications(
    db: AsyncSession,
    page: int = 1,
    page_size: int = DEFAULT_PAGE_SIZE,
    status: str | None = None,
) -> ApplicationListResponse:
    """List applications with pagination and optional status filter.

    Args:
        db: Async database session.
        page: Page number (1-indexed).
        page_size: Items per page.
        status: Optional status filter.

    Returns:
        Paginated application list response.
    """
    page_size = min(page_size, MAX_PAGE_SIZE)
    offset = (page - 1) * page_size

    query = select(Application).options(selectinload(Application.job))
    count_query = select(func.count(Application.id))

    if status:
        query = query.where(Application.status == status)
        count_query = count_query.where(Application.status == status)

    query = query.order_by(Application.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    apps = list(result.scalars().all())

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    items = [application_to_response(app) for app in apps]

    return ApplicationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_next=(page * page_size) < total,
    )


async def get_application(db: AsyncSession, app_id: str) -> Application:
    """Get a single application by ID.

    Args:
        db: Async database session.
        app_id: UUID of the application.

    Returns:
        The Application model instance.

    Raises:
        RecordNotFoundError: If application does not exist.
    """
    result = await db.execute(
        select(Application)
        .where(Application.id == app_id)
        .options(selectinload(Application.job)),
    )
    app = result.scalar_one_or_none()
    if app is None:
        raise RecordNotFoundError("Application", app_id)
    return app


async def approve_application(db: AsyncSession, app_id: str) -> Application:
    """Approve a pending application for submission.

    Args:
        db: Async database session.
        app_id: UUID of the application to approve.

    Returns:
        The updated Application.

    Raises:
        RecordNotFoundError: If application does not exist.
    """
    app = await get_application(db, app_id)
    if app.status not in (ApplicationStatus.PENDING_REVIEW, ApplicationStatus.QUEUED):
        raise ValueError(
            f"Cannot approve application in '{app.status}' state. "
            "Only pending_review or queued applications can be approved."
        )
    app.status = ApplicationStatus.APPROVED
    await db.commit()
    await db.refresh(app)
    logger.info("application_approved", app_id=app_id)
    return app


async def update_status(
    db: AsyncSession,
    app_id: str,
    update: ApplicationStatusUpdate,
) -> Application:
    """Update an application's status and optional notes.

    Args:
        db: Async database session.
        app_id: UUID of the application.
        update: Status update payload.

    Returns:
        The updated Application.

    Raises:
        RecordNotFoundError: If application does not exist.
    """
    app = await get_application(db, app_id)
    app.status = update.status
    if update.notes is not None:
        app.notes = update.notes
    if update.status == ApplicationStatus.APPLIED:
        app.applied_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(app)
    logger.info("application_status_updated", app_id=app_id, status=update.status)
    return app
