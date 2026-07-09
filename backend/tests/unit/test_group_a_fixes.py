"""Group A remediation regression tests: login timing, LLM cost/fallback, timeline,
cross-tenant FK validation, bulk_approve state guard."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.exceptions import LLMProviderError, RecordNotFoundError
from app.core.llm.client import LLMClient
from app.models.application import Application
from app.models.enums import ApplicationStatus, ApplyMode
from app.models.job import Job
from app.models.user import User
from app.schemas.application import ApplicationBatchCreate, ApplicationCreate
from app.services import analytics, dispatch
from app.services import application as app_service
from tests.conftest import TEST_USER_ID
from tests.unit.test_llm_client import _make_completion_response, _make_settings_mock


def _job(platform_job_id: str, owner: str = TEST_USER_ID) -> Job:
    return Job(
        user_id=owner, platform="linkedin", platform_job_id=platform_job_id,
        title="t", company="c", url="https://x",
    )


def _llm_client() -> LLMClient:
    with patch("app.core.llm.client.get_settings", return_value=_make_settings_mock()):
        with patch("app.core.llm.client.litellm"):
            return LLMClient()


# --- A1: login enumeration ---------------------------------------------------


class TestLoginTiming:
    async def test_verify_runs_even_for_unknown_email(self, anon_client):
        # An unknown email must still trigger the (slow) Argon2 verify against DUMMY_HASH,
        # so the timing does not reveal whether the account exists.
        with patch("app.api.v1.auth.verify_password", return_value=False) as spy:
            r = await anon_client.post(
                "/api/v1/auth/login",
                data={"username": "nobody@nowhere.com", "password": "x"},
            )
        assert r.status_code == 401
        spy.assert_called_once()
        assert spy.call_args.args[1] is None  # called with hashed=None -> DUMMY_HASH path


# --- A2 / A3: LLM client cost + fallback ------------------------------------


class TestLLMClientRobustness:
    async def test_cost_failure_degrades_to_zero(self):
        client = _llm_client()
        with patch("app.core.llm.client.litellm") as ml:
            ml.acompletion = AsyncMock(return_value=_make_completion_response("ok"))
            ml.completion_cost.side_effect = Exception("model not in cost map")
            ml.Usage = MagicMock
            result = await client.complete("prompt")
        assert result.content == "ok"
        assert result.cost_usd == 0.0  # billed call did not crash on a pricing-map miss

    async def test_unexpected_error_raises_typed_not_raw(self):
        client = _llm_client()
        with patch("app.core.llm.client.litellm") as ml:
            ml.RateLimitError = type("RL", (Exception,), {})
            ml.Timeout = type("TO", (Exception,), {})
            ml.APIError = type("APIErr", (Exception,), {})
            # e.g. AuthenticationError — NOT an APIError subclass — must not escape raw.
            ml.acompletion = AsyncMock(side_effect=ValueError("invalid api key"))
            ml.Usage = MagicMock
            with pytest.raises(LLMProviderError):
                await client.complete("prompt")


# --- A4: timeline aggregation -----------------------------------------------


class TestTimelineAggregation:
    async def test_sums_same_day_across_distinct_seconds(self, db_session):
        day = datetime(2026, 6, 16, tzinfo=UTC)
        for i in range(3):
            job = _job(f"tl-{i}")
            db_session.add(job)
            await db_session.flush()
            db_session.add(
                Application(
                    user_id=TEST_USER_ID, job_id=job.id, status=ApplicationStatus.QUEUED,
                    apply_mode=ApplyMode.REVIEW,
                    created_at=day.replace(second=i * 10),
                )
            )
        await db_session.commit()

        timeline = await analytics.get_timeline(db_session)
        entry = next(e for e in timeline if e.date == "2026-06-16")
        assert entry.applications_created == 3  # not 1 (the old last-write-wins bug)


# --- A5: cross-tenant FK validation -----------------------------------------


class TestCrossTenantCreate:
    async def _foreign_job(self, db_session) -> Job:
        db_session.add(User(id="other-user", email="o@x.com", hashed_password="x"))
        job = _job("foreign-1", owner="other-user")
        db_session.add(job)
        await db_session.commit()
        return job

    async def test_create_application_rejects_foreign_job(self, db_session):
        foreign = await self._foreign_job(db_session)
        with pytest.raises(RecordNotFoundError):
            await app_service.create_application(
                db_session, ApplicationCreate(job_id=foreign.id), TEST_USER_ID
            )
        rows = (await db_session.execute(select(Application))).scalars().all()
        assert rows == []  # no cross-tenant row created

    async def test_create_batch_rejects_foreign_job(self, db_session):
        foreign = await self._foreign_job(db_session)
        own = _job("own-1")
        db_session.add(own)
        await db_session.commit()
        with pytest.raises(RecordNotFoundError):
            await app_service.create_batch(
                db_session, ApplicationBatchCreate(job_ids=[own.id, foreign.id]), TEST_USER_ID
            )


# --- A6: bulk_approve state guard -------------------------------------------


class TestBulkApproveGuard:
    async def test_only_approvable_states_transition(self, db_session):
        job_a, job_b = _job("ba-1"), _job("ba-2")
        db_session.add_all([job_a, job_b])
        await db_session.flush()
        pending = Application(
            user_id=TEST_USER_ID, job_id=job_a.id,
            status=ApplicationStatus.PENDING_REVIEW, apply_mode=ApplyMode.BATCH,
        )
        applied = Application(
            user_id=TEST_USER_ID, job_id=job_b.id,
            status=ApplicationStatus.APPLIED, apply_mode=ApplyMode.BATCH,
        )
        db_session.add_all([pending, applied])
        await db_session.commit()
        await db_session.refresh(pending)
        await db_session.refresh(applied)

        count = await dispatch.bulk_approve(db_session, None, [pending.id, applied.id])

        assert count == 1
        await db_session.refresh(pending)
        await db_session.refresh(applied)
        assert pending.status == ApplicationStatus.APPROVED
        assert applied.status == ApplicationStatus.APPLIED  # terminal row untouched
