"""Phase 4 W3: GDPR account deletion (D9) — hard purge, soft-delete endpoint, purge cron."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import select

from app.core.harness import record
from app.models.application import Application
from app.models.enums import ApplicationStatus, ApplyMode, LLMPurpose
from app.models.job import Job
from app.models.llm_usage import LLMUsage
from app.models.resume import Resume
from app.models.user import User
from app.models.user_credential import UserCredential
from app.services import account
from app.workers import tasks
from tests.conftest import TEST_USER_ID


class _SessionCM:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


async def _unscoped(db, model):
    return (
        await db.execute(select(model).execution_options(skip_tenant_filter=True))
    ).scalars().all()


class TestDeleteUserData:
    async def test_removes_all_owned_rows_and_files(self, db_session):
        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        job = Job(
            user_id=TEST_USER_ID, platform="linkedin", platform_job_id="j1",
            title="t", company="c", url="https://x",
        )
        db_session.add(job)
        await db_session.flush()
        db_session.add(
            Application(
                user_id=TEST_USER_ID, job_id=job.id,
                status=ApplicationStatus.QUEUED, apply_mode=ApplyMode.REVIEW,
            )
        )
        db_session.add(Resume(user_id=TEST_USER_ID, name="r", type="base", template_id="modern"))
        db_session.add(
            LLMUsage(user_id=TEST_USER_ID, provider="openai", model="gpt-4o", purpose=LLMPurpose.GENERAL)
        )
        db_session.add(
            UserCredential(user_id=TEST_USER_ID, kind="llm_key", provider="openai", blob={}, kek_id="k")
        )
        await db_session.commit()
        await record.record_trajectory(
            db_session, user_id=TEST_USER_ID, application_id="app-1", platform="linkedin"
        )

        mock_storage = MagicMock()
        mock_storage.delete_prefix = AsyncMock(return_value=2)
        with patch.object(account, "get_storage", return_value=mock_storage):
            result = await account.delete_user_data(db_session, TEST_USER_ID)

        mock_storage.delete_prefix.assert_awaited_once()
        # Trailing slash confines deletion to this user's tree (not "users/u10..." siblings).
        assert mock_storage.delete_prefix.await_args.args[0] == f"users/{TEST_USER_ID}/"
        assert result["files_removed"] == 2
        for model in (User, Job, Application, Resume, LLMUsage, UserCredential):
            assert await _unscoped(db_session, model) == [], model.__name__


class TestSoftDeleteEndpoint:
    async def test_delete_account_soft_deletes_and_blocks_token(self, anon_client):
        creds = {"email": "u@x.com", "password": "password123"}
        await anon_client.post("/api/v1/auth/register", json=creds)
        token = (
            await anon_client.post(
                "/api/v1/auth/login", data={"username": "u@x.com", "password": "password123"}
            )
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        assert (await anon_client.delete("/api/v1/auth/account", headers=headers)).status_code == 204
        # The account is now soft-deleted → its access token is rejected.
        assert (await anon_client.get("/api/v1/auth/me", headers=headers)).status_code == 401


class TestPurgeCron:
    async def test_purges_only_expired_soft_deletes(self, db_session):
        old = datetime.now(UTC) - timedelta(days=account.PURGE_GRACE_DAYS + 1)
        recent = datetime.now(UTC) - timedelta(days=5)
        db_session.add(User(id="old-user", email="o@x.com", hashed_password="x", deleted_at=old))
        db_session.add(User(id="recent-user", email="r@x.com", hashed_password="x", deleted_at=recent))
        db_session.add(User(id="active-user", email="a@x.com", hashed_password="x"))
        await db_session.commit()

        storage = MagicMock()
        storage.delete_prefix = AsyncMock(return_value=0)
        with patch.object(tasks, "async_session_factory", lambda: _SessionCM(db_session)), patch.object(
            account, "get_storage", return_value=storage
        ):
            await tasks.purge_deleted_accounts({"redis": None})

        remaining = {u for u in (await db_session.execute(
            select(User.id).execution_options(skip_tenant_filter=True)
        )).scalars().all()}
        assert remaining == {"recent-user", "active-user"}  # old-user hard-purged
