"""Phase 1.2: the Arq apply pipeline — idempotency, status lifecycle, retry classification."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from arq import Retry

from app.models.application import Application
from app.models.enums import ApplicationStatus, ApplyMode
from app.models.job import Job
from app.workers import tasks
from tests.conftest import TEST_USER_ID

CTX = {"job_try": 1, "redis": None}


async def _seed_app(db, sample_job_data, status=ApplicationStatus.QUEUED) -> Application:
    job = Job(**sample_job_data)
    db.add(job)
    await db.flush()
    app = Application(
        user_id=TEST_USER_ID, job_id=job.id, status=status, apply_mode=ApplyMode.AUTONOMOUS
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


class TestApplyPipeline:
    async def test_successful_apply_marks_applied(self, db_session, sample_job_data):
        app = await _seed_app(db_session, sample_job_data)
        await tasks._apply(db_session, CTX, app.id)
        await db_session.refresh(app)
        assert app.status == ApplicationStatus.APPLIED
        assert app.applied_at is not None

    async def test_terminal_outcome_emits_metric(self, db_session, sample_job_data):
        platform = sample_job_data["platform"]
        gauge = tasks.applications_total.labels(status="applied", platform=platform)
        before = gauge._value.get()
        app = await _seed_app(db_session, sample_job_data)
        await tasks._apply(db_session, CTX, app.id)
        assert gauge._value.get() == before + 1

    async def test_idempotent_when_already_applied(self, db_session, sample_job_data):
        app = await _seed_app(db_session, sample_job_data, status=ApplicationStatus.APPLIED)
        with patch.object(tasks, "_submit_application", new=AsyncMock()) as submit:
            await tasks._apply(db_session, CTX, app.id)
            submit.assert_not_awaited()

    async def test_transient_error_raises_retry_and_keeps_applying(
        self, db_session, sample_job_data
    ):
        app = await _seed_app(db_session, sample_job_data)
        with patch.object(
            tasks,
            "_submit_application",
            new=AsyncMock(side_effect=tasks.TransientApplyError("blip")),
        ):
            with pytest.raises(Retry):
                await tasks._apply(db_session, CTX, app.id)
        await db_session.refresh(app)
        assert app.status == ApplicationStatus.APPLYING  # in-flight marker persisted

    async def test_permanent_error_marks_failed(self, db_session, sample_job_data):
        app = await _seed_app(db_session, sample_job_data)
        with patch.object(
            tasks, "_submit_application", new=AsyncMock(side_effect=ValueError("boom"))
        ):
            await tasks._apply(db_session, CTX, app.id)
        await db_session.refresh(app)
        assert app.status == ApplicationStatus.FAILED
        assert "boom" in (app.notes or "")

    async def test_missing_application_is_noop(self, db_session):
        await tasks._apply(db_session, CTX, "nonexistent-id")  # must not raise

    async def test_retry_exhaustion_marks_failed_not_stuck_applying(
        self, db_session, sample_job_data
    ):
        # On the final attempt a persistent transient failure must transition to terminal
        # FAILED (not raise Retry and leave the row stuck in APPLYING forever).
        app = await _seed_app(db_session, sample_job_data)
        ctx = {"job_try": tasks.MAX_TRIES, "redis": None}
        with patch.object(
            tasks, "_submit_application",
            new=AsyncMock(side_effect=tasks.TransientApplyError("anti-bot wall")),
        ):
            await tasks._apply(db_session, ctx, app.id)  # must NOT raise Retry
        await db_session.refresh(app)
        assert app.status == ApplicationStatus.FAILED
        assert "attempts" in (app.notes or "")


class TestTransientClassification:
    def test_is_transient(self):
        assert tasks._is_transient(RuntimeError("Rate limit exceeded (429)"))
        assert tasks._is_transient(RuntimeError("Connection reset by peer"))
        assert tasks._is_transient(RuntimeError("service temporarily unavailable"))
        assert not tasks._is_transient(RuntimeError("required form field missing"))

    async def test_submit_reclassifies_transient_infra_error(self, db_session, sample_job_data):
        app = await _seed_app(db_session, sample_job_data)
        fake_settings = MagicMock()
        fake_settings.browser.live_apply = True
        with patch.object(tasks, "get_settings", return_value=fake_settings), patch(
            "app.core.automation.runtime.apply.run_apply",
            new=AsyncMock(side_effect=RuntimeError("429 Too Many Requests")),
        ):
            with pytest.raises(tasks.TransientApplyError):
                await tasks._submit_application(db_session, app)

    async def test_submit_keeps_terminal_error_terminal(self, db_session, sample_job_data):
        app = await _seed_app(db_session, sample_job_data)
        fake_settings = MagicMock()
        fake_settings.browser.live_apply = True
        with patch.object(tasks, "get_settings", return_value=fake_settings), patch(
            "app.core.automation.runtime.apply.run_apply",
            new=AsyncMock(side_effect=RuntimeError("required form field missing")),
        ):
            with pytest.raises(RuntimeError) as exc:  # NOT reclassified to TransientApplyError
                await tasks._submit_application(db_session, app)
            assert not isinstance(exc.value, tasks.TransientApplyError)


class TestPublish:
    async def test_publish_no_redis_is_noop(self):
        await tasks._publish({"redis": None}, TEST_USER_ID, "app-1", "applying")
