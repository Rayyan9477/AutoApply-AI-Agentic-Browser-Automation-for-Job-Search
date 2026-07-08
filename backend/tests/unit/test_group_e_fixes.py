"""Group E remediation regression tests: active-application dedup (idempotent create +
batch skip) and queue_depth gauge set on enqueue."""

from unittest.mock import AsyncMock, MagicMock

from sqlalchemy import select

from app.models.application import Application
from app.models.enums import ApplicationStatus, ApplyMode
from app.models.job import Job
from app.schemas.application import ApplicationBatchCreate, ApplicationCreate
from app.services import application as app_service
from app.services import dispatch
from tests.conftest import TEST_USER_ID


def _job(platform_job_id: str) -> Job:
    return Job(
        user_id=TEST_USER_ID, platform="linkedin", platform_job_id=platform_job_id,
        title="t", company="c", url="https://x",
    )


class TestActiveApplicationDedup:
    async def test_duplicate_create_returns_existing(self, db_session):
        job = _job("dup-1")
        db_session.add(job)
        await db_session.commit()
        await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id), TEST_USER_ID
        )
        await app_service.create_application(  # idempotent: must not create a duplicate
            db_session, ApplicationCreate(job_id=job.id), TEST_USER_ID
        )
        rows = (
            await db_session.execute(select(Application).where(Application.job_id == job.id))
        ).scalars().all()
        assert len(rows) == 1

    async def test_reapply_allowed_after_terminal(self, db_session):
        job = _job("dup-2")
        db_session.add(job)
        await db_session.commit()
        first = await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id), TEST_USER_ID
        )
        first.status = ApplicationStatus.FAILED  # terminal → frees the slot
        await db_session.commit()
        second = await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id), TEST_USER_ID
        )
        assert second.id != first.id  # a fresh application is allowed

    async def test_batch_skips_jobs_with_active_application(self, db_session):
        job_a, job_b = _job("ba-1"), _job("ba-2")
        db_session.add_all([job_a, job_b])
        await db_session.flush()
        db_session.add(
            Application(
                user_id=TEST_USER_ID, job_id=job_a.id,
                status=ApplicationStatus.QUEUED, apply_mode=ApplyMode.REVIEW,
            )
        )
        await db_session.commit()

        created = await app_service.create_batch(
            db_session, ApplicationBatchCreate(job_ids=[job_a.id, job_b.id]), TEST_USER_ID
        )
        assert {a.job_id for a in created} == {job_b.id}  # job_a skipped (already active)


class TestEnqueueSetsQueueDepth:
    async def test_enqueue_sets_gauge(self):
        pool = MagicMock()
        job = MagicMock()
        job.job_id = "apply:app-1"
        pool.enqueue_job = AsyncMock(return_value=job)
        pool.llen = AsyncMock(return_value=7)
        gauge = dispatch.queue_depth.labels(queue_name=dispatch._ARQ_QUEUE)

        await dispatch.enqueue_apply(pool, "app-1")

        assert gauge._value.get() == 7
