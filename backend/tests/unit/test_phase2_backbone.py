"""Phase 2 backbone: encrypted session-cookie store, intervention rendezvous, runtime."""

import fakeredis.aioredis
import pytest
from cryptography.fernet import Fernet

from app.core.automation.intervention import request_intervention, resolve_intervention
from app.core.automation.runtime.apply import ApplyPrerequisiteError, run_apply
from app.core.automation.runtime.factory import build_browser_profile
from app.core.automation.runtime.result import ApplicationResult
from app.core.secrets import CredentialStore
from app.core.secrets.local import LocalSecretsProvider
from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from tests.conftest import TEST_USER_ID


def _store() -> CredentialStore:
    return CredentialStore(LocalSecretsProvider([Fernet.generate_key().decode()]))


class TestSessionCookieStore:
    async def test_roundtrip(self, db_session):
        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db_session.commit()
        store = _store()
        state = {"cookies": [{"name": "li_at", "value": "secret"}], "origins": []}

        await store.save_session_cookies(db_session, TEST_USER_ID, "linkedin", state)
        loaded = await store.load_session_cookies(db_session, TEST_USER_ID, "linkedin")

        assert loaded == state

    async def test_missing_returns_none(self, db_session):
        store = _store()
        assert await store.load_session_cookies(db_session, TEST_USER_ID, "indeed") is None


class TestInterventionRendezvous:
    async def test_resolve_then_request(self):
        redis = fakeredis.aioredis.FakeRedis()
        await resolve_intervention(redis, "app-1", "123456")
        assert await request_intervention(redis, "app-1", timeout=1) == "123456"

    async def test_request_times_out(self):
        redis = fakeredis.aioredis.FakeRedis()
        assert await request_intervention(redis, "app-2", timeout=1) is None


class TestRuntimeFactory:
    def test_application_result_defaults(self):
        result = ApplicationResult()
        assert result.submitted is False
        assert result.confirmation_id is None

    def test_build_browser_profile_carries_session_and_identity(self):
        state = {"cookies": [], "origins": []}
        profile = build_browser_profile(
            storage_state=state,
            user_agent="UA/1.0",
            allowed_domains=["*.linkedin.com"],
            headless=True,
        )
        assert profile.storage_state == state
        assert profile.user_agent == "UA/1.0"
        assert profile.headless is True
        assert profile.allowed_domains == ["*.linkedin.com"]


class TestRunApplyPrerequisites:
    """run_apply must fail clearly (no browser launched) when setup is incomplete."""

    async def _seed(self, db, *, with_resume: bool):
        db.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        job = Job(
            user_id=TEST_USER_ID, platform="linkedin", platform_job_id="j1",
            title="t", company="c", url="https://x",
        )
        db.add(job)
        await db.flush()
        resume_id = None
        if with_resume:
            resume = Resume(
                user_id=TEST_USER_ID, name="r", type="base",
                template_id="modern", file_path_pdf="/tmp/r.pdf",
            )
            db.add(resume)
            await db.flush()
            resume_id = resume.id
        app = Application(
            user_id=TEST_USER_ID, job_id=job.id, resume_id=resume_id,
            status="queued", apply_mode="autonomous",
        )
        db.add(app)
        await db.commit()
        await db.refresh(app)
        return app

    async def test_missing_resume_raises(self, db_session):
        app = await self._seed(db_session, with_resume=False)
        with pytest.raises(ApplyPrerequisiteError):
            await run_apply(db_session, app)

    async def test_missing_session_raises(self, db_session):
        app = await self._seed(db_session, with_resume=True)
        with pytest.raises(ApplyPrerequisiteError):
            await run_apply(db_session, app)
