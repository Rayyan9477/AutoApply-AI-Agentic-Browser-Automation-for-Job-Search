"""Account lifecycle: soft-delete + hard purge (GDPR / D9).

``delete_user_data`` removes ALL of a user's data — every owned DB row, their stored files
(storage ``users/{uid}/`` prefix), and their encrypted credentials. Deletes are explicit and
child-first so they're deterministic on SQLite (no FK-pragma dependency) and Postgres alike.
Shared, non-tenant data (DomainSkill knowledge) is intentionally NOT removed.
"""

from __future__ import annotations

import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_storage, keys
from app.core.storage.service import StorageService
from app.models.application import Application
from app.models.harness import RunDiagnosis, RunTrajectory, RunVerdict
from app.models.job import Job
from app.models.llm_usage import LLMUsage
from app.models.platform_session import PlatformSession
from app.models.refresh_token import RefreshToken
from app.models.resume import Resume
from app.models.user import User
from app.models.user_credential import UserCredential
from app.models.user_llm_config import UserLLMConfig
from app.models.user_settings import UserSettings

logger = structlog.get_logger(__name__)

PURGE_GRACE_DAYS = 30  # soft-deleted accounts are hard-purged after this many days

# Child-before-parent so the deletes never violate a FK regardless of dialect / FK pragma.
_OWNED_MODELS_IN_DELETE_ORDER = (
    RunVerdict,
    RunDiagnosis,
    RunTrajectory,
    Application,
    Resume,
    Job,
    LLMUsage,
    UserCredential,
    UserLLMConfig,
    UserSettings,
    PlatformSession,
    RefreshToken,
)


async def delete_user_data(db: AsyncSession, user_id: str) -> dict[str, int]:
    """Hard-delete every artifact belonging to ``user_id`` (files + DB rows + credentials)."""
    # 1. Stored files FIRST. The trailing "/" confines deletion to this user's tree — a bare
    #    "users/u1" prefix would also match "users/u10/..." (S3 prefix is substring-based). If
    #    storage deletion fails we ABORT (don't touch the DB) so the daily purge retries the
    #    still-soft-deleted account rather than orphaning files behind a deleted user row.
    try:
        files_removed = await StorageService(get_storage(), user_id).delete_prefix(
            keys.user_prefix(user_id) + "/"
        )
    except Exception as exc:
        logger.warning("purge.storage_failed_will_retry", user_id=user_id, error=str(exc))
        return {"rows_deleted": 0, "files_removed": 0, "purged": 0}

    # 2. DB rows — explicit, child-first, tenant filter bypassed (admin op).
    rows_deleted = 0
    for model in _OWNED_MODELS_IN_DELETE_ORDER:
        result = await db.execute(
            delete(model)
            .where(model.user_id == user_id)
            .execution_options(skip_tenant_filter=True)
        )
        rows_deleted += result.rowcount or 0
    await db.execute(delete(User).where(User.id == user_id))
    await db.commit()

    logger.info("purge.user_data_deleted", user_id=user_id, rows=rows_deleted, files=files_removed)
    return {"rows_deleted": rows_deleted, "files_removed": files_removed, "purged": 1}
