"""Phase 1.1: apply-mode dispatch + the enqueue producer."""

from unittest.mock import AsyncMock

from app.models.enums import ApplicationStatus, ApplyMode
from app.models.job import Job
from app.schemas.application import ApplicationCreate
from app.services import application as app_service
from app.services import dispatch
from tests.conftest import TEST_USER_ID


class _FakeJob:
    job_id = "job-xyz"


def _fake_pool() -> AsyncMock:
    pool = AsyncMock()
    pool.enqueue_job = AsyncMock(return_value=_FakeJob())
    return pool


async def _job(db, sample_job_data, suffix="0") -> Job:
    job = Job(**{**sample_job_data, "platform_job_id": f"job-{suffix}"})
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def _make_app(db, job_id, mode):
    return await app_service.create_application(
        db, ApplicationCreate(job_id=job_id, apply_mode=mode), TEST_USER_ID
    )


class TestDispatchForMode:
    async def test_autonomous_enqueues_and_queues(self, db_session, sample_job_data):
        job = await _job(db_session, sample_job_data)
        app = await _make_app(db_session, job.id, ApplyMode.AUTONOMOUS)
        pool = _fake_pool()

        await dispatch.dispatch_for_mode(db_session, pool, app)

        assert app.status == ApplicationStatus.QUEUED
        pool.enqueue_job.assert_awaited_once()
        assert pool.enqueue_job.call_args.kwargs["_job_id"] == f"apply:{app.id}"

    async def test_review_stages_without_enqueue(self, db_session, sample_job_data):
        job = await _job(db_session, sample_job_data)
        app = await _make_app(db_session, job.id, ApplyMode.REVIEW)
        pool = _fake_pool()

        await dispatch.dispatch_for_mode(db_session, pool, app)

        assert app.status == ApplicationStatus.PENDING_REVIEW
        pool.enqueue_job.assert_not_awaited()

    async def test_batch_stages_without_enqueue(self, db_session, sample_job_data):
        job = await _job(db_session, sample_job_data)
        app = await _make_app(db_session, job.id, ApplyMode.BATCH)
        pool = _fake_pool()

        await dispatch.dispatch_for_mode(db_session, pool, app)

        assert app.status == ApplicationStatus.PENDING_REVIEW
        pool.enqueue_job.assert_not_awaited()


class TestBulkApprove:
    async def test_bulk_approve_enqueues_each(self, db_session, sample_job_data):
        pool = _fake_pool()
        ids = []
        for i in range(2):
            job = await _job(db_session, sample_job_data, suffix=str(i))
            app = await _make_app(db_session, job.id, ApplyMode.BATCH)
            await dispatch.dispatch_for_mode(db_session, pool, app)
            ids.append(app.id)
        pool.enqueue_job.reset_mock()

        count = await dispatch.bulk_approve(db_session, pool, ids)

        assert count == 2
        assert pool.enqueue_job.await_count == 2


class TestEnqueueWithoutPool:
    async def test_enqueue_without_pool_is_noop(self):
        assert await dispatch.enqueue_apply(None, "app-1") is None
