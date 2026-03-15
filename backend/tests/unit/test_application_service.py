"""Unit tests for the application service."""

import pytest

from app.config.constants import ApplicationStatus
from app.core.exceptions import RecordNotFoundError
from app.models.job import Job
from app.schemas.application import (
    ApplicationBatchCreate,
    ApplicationCreate,
    ApplicationStatusUpdate,
)
from app.services import application as app_service


async def _create_job(db_session, sample_job_data, suffix="0"):
    """Helper to create a job and return it."""
    data = {**sample_job_data, "platform_job_id": f"job-{suffix}"}
    job = Job(**data)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


class TestCreateApplication:
    async def test_create_application(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)
        data = ApplicationCreate(job_id=job.id)
        app = await app_service.create_application(db_session, data)

        assert app.id is not None
        assert app.job_id == job.id
        assert app.status == ApplicationStatus.QUEUED
        assert app.apply_mode == "review"
        assert app.resume_id is None


class TestCreateBatch:
    async def test_create_batch(self, db_session, sample_job_data):
        jobs = []
        for i in range(3):
            jobs.append(await _create_job(db_session, sample_job_data, suffix=str(i)))

        data = ApplicationBatchCreate(job_ids=[j.id for j in jobs])
        apps = await app_service.create_batch(db_session, data)

        assert len(apps) == 3
        job_ids = {a.job_id for a in apps}
        assert job_ids == {j.id for j in jobs}


class TestListApplications:
    async def test_list_applications_empty(self, db_session):
        result = await app_service.list_applications(db_session)
        assert result.items == []
        assert result.total == 0

    async def test_list_applications_with_data(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)
        for _ in range(3):
            data = ApplicationCreate(job_id=job.id)
            await app_service.create_application(db_session, data)

        result = await app_service.list_applications(db_session, page=1, page_size=2)
        assert len(result.items) == 2
        assert result.total == 3
        assert result.has_next is True

    async def test_list_applications_filter_status(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)

        # Create two QUEUED apps
        for _ in range(2):
            await app_service.create_application(
                db_session, ApplicationCreate(job_id=job.id)
            )

        # Create one and approve it
        app_obj = await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id)
        )
        await app_service.approve_application(db_session, app_obj.id)

        queued = await app_service.list_applications(
            db_session, status=ApplicationStatus.QUEUED
        )
        assert queued.total == 2

        approved = await app_service.list_applications(
            db_session, status=ApplicationStatus.APPROVED
        )
        assert approved.total == 1


class TestGetApplication:
    async def test_get_application_found(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)
        created = await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id)
        )

        found = await app_service.get_application(db_session, created.id)
        assert found.id == created.id
        assert found.job_id == job.id

    async def test_get_application_not_found(self, db_session):
        with pytest.raises(RecordNotFoundError):
            await app_service.get_application(db_session, "nonexistent_id")


class TestApproveApplication:
    async def test_approve_application(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)
        created = await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id)
        )
        assert created.status == ApplicationStatus.QUEUED

        approved = await app_service.approve_application(db_session, created.id)
        assert approved.status == ApplicationStatus.APPROVED


class TestUpdateStatus:
    async def test_update_status_with_notes(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)
        created = await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id)
        )

        update = ApplicationStatusUpdate(status=ApplicationStatus.REJECTED, notes="Not a fit")
        updated = await app_service.update_status(db_session, created.id, update)

        assert updated.status == ApplicationStatus.REJECTED
        assert updated.notes == "Not a fit"

    async def test_update_status_applied_sets_timestamp(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)
        created = await app_service.create_application(
            db_session, ApplicationCreate(job_id=job.id)
        )
        assert created.applied_at is None

        update = ApplicationStatusUpdate(status=ApplicationStatus.APPLIED)
        updated = await app_service.update_status(db_session, created.id, update)

        assert updated.status == ApplicationStatus.APPLIED
        assert updated.applied_at is not None
