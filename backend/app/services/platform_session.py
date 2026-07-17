"""Platform session service: import, list, and delete per-user browser sessions.

The encrypted ``storage_state`` lives in ``user_credentials`` (via :class:`CredentialStore`);
the ``platform_sessions`` row holds the cookie-free verification metadata the worker consults
before an apply run. Both are keyed by an explicit ``user_id`` (neither is a tenant entity).
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets.credential_store import CredentialStore
from app.models.platform_session import PlatformSession
from app.schemas.platform_session import PlatformSessionResponse

logger = structlog.get_logger(__name__)


def _fingerprint(storage_state: dict[str, Any]) -> str:
    """A stable hash of the session, so a re-import can be recognised as the same login."""
    return hashlib.sha256(json.dumps(storage_state, sort_keys=True).encode()).hexdigest()


def to_response(row: PlatformSession) -> PlatformSessionResponse:
    """Project a stored session to its cookie-free public view."""
    return PlatformSessionResponse(
        platform=row.platform,
        connected=True,
        last_verified_at=row.last_verified_at,
        expires_at=row.expires_at,
    )


async def import_session(
    db: AsyncSession,
    user_id: str,
    platform: str,
    storage_state: dict[str, Any],
    *,
    expires_at: datetime | None = None,
) -> PlatformSession:
    """Encrypt+store the storage_state and upsert the platform-session metadata row."""
    await CredentialStore().save_session_cookies(db, user_id, platform, storage_state)

    now = datetime.now(UTC)
    fingerprint = _fingerprint(storage_state)
    row = (
        await db.execute(
            select(PlatformSession).where(
                PlatformSession.user_id == user_id, PlatformSession.platform == platform
            )
        )
    ).scalar_one_or_none()
    if row is None:
        row = PlatformSession(
            user_id=user_id,
            platform=platform,
            last_verified_at=now,
            expires_at=expires_at,
            fingerprint_hash=fingerprint,
        )
        db.add(row)
    else:
        row.last_verified_at = now
        row.expires_at = expires_at
        row.fingerprint_hash = fingerprint
    await db.commit()
    await db.refresh(row)
    logger.info("platform_session_imported", user_id=user_id, platform=platform)
    return row


async def list_sessions(db: AsyncSession, user_id: str) -> list[PlatformSession]:
    """Return the user's stored platform sessions (metadata only)."""
    result = await db.execute(
        select(PlatformSession)
        .where(PlatformSession.user_id == user_id)
        .order_by(PlatformSession.platform)
    )
    return list(result.scalars().all())


async def delete_session(db: AsyncSession, user_id: str, platform: str) -> bool:
    """Remove a platform's session (cookies + metadata). Returns True if anything was removed."""
    had_cookies = await CredentialStore().delete_session_cookies(db, user_id, platform)
    result = await db.execute(
        delete(PlatformSession).where(
            PlatformSession.user_id == user_id, PlatformSession.platform == platform
        )
    )
    await db.commit()
    removed = had_cookies or result.rowcount > 0
    if removed:
        logger.info("platform_session_deleted", user_id=user_id, platform=platform)
    return removed
