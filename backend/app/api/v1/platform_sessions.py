"""Platform session routes: import / list / disconnect a job-platform login for the apply agent.

The apply worker cannot log a user into LinkedIn/Indeed/etc. unattended; instead the user's
captured browser ``storage_state`` is imported here (encrypted at rest) and later loaded into the
browser context by ``run_apply``. Cookies are never returned by any endpoint.
"""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.core.exceptions import RecordNotFoundError
from app.schemas.platform_session import PlatformSessionImport, PlatformSessionResponse
from app.services import platform_session as service

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=PlatformSessionResponse,
    status_code=201,
    summary="Import a platform session",
)
async def import_session(
    data: PlatformSessionImport,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PlatformSessionResponse:
    """Persist an encrypted browser session so the apply agent can reuse the login."""
    row = await service.import_session(
        db, user.id, data.platform, data.storage_state, expires_at=data.expires_at
    )
    return service.to_response(row)


@router.get(
    "/", response_model=list[PlatformSessionResponse], summary="List connected platform sessions"
)
async def list_sessions(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[PlatformSessionResponse]:
    """List the current user's connected platform sessions (metadata only, no cookies)."""
    rows = await service.list_sessions(db, user.id)
    return [service.to_response(r) for r in rows]


@router.delete("/{platform}", status_code=204, summary="Disconnect a platform session")
async def delete_session(
    platform: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a stored platform session and its cookies. 404 if none was connected."""
    removed = await service.delete_session(db, user.id, platform.strip().lower())
    if not removed:
        raise RecordNotFoundError("No stored session for that platform")
