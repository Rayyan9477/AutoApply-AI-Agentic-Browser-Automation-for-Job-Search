"""F3: service create paths set ``user_id`` on INSERT (not auto-scoped by the filter)."""

import pytest
from sqlalchemy import select

from app.db.tenant import current_user_id
from app.models.application import Application
from app.models.job import Job
from app.models.user import User
from app.schemas.application import ApplicationBatchCreate, ApplicationCreate
from app.services import application as app_service

UID = "c" * 32


@pytest.fixture()
def _scope_to_uid():
    # In production the ambient tenant (get_tenant_db) always equals the user_id the
    # service is called with; these tests pass UID, so scope the filter to UID too.
    token = current_user_id.set(UID)
    yield
    current_user_id.reset(token)


async def _job(db) -> Job:
    job = Job(user_id=UID, platform="linkedin", platform_job_id="j", title="t", company="c", url="u")
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def _read_unscoped(db, app_id: str) -> Application:
    """Read a row bypassing the tenant filter, to inspect the raw user_id."""
    return (
        await db.execute(
            select(Application)
            .where(Application.id == app_id)
            .execution_options(skip_tenant_filter=True)
        )
    ).scalar_one()


class TestInsertSetsUserId:
    async def test_create_application_sets_user_id(self, db_session, _scope_to_uid):
        db_session.add(User(id=UID, email="i@x.com", hashed_password="x"))
        job = await _job(db_session)

        app = await app_service.create_application(db_session, ApplicationCreate(job_id=job.id), UID)

        row = await _read_unscoped(db_session, app.id)
        assert row.user_id == UID

    async def test_create_batch_sets_user_id(self, db_session, _scope_to_uid):
        db_session.add(User(id=UID, email="i@x.com", hashed_password="x"))
        job = await _job(db_session)

        apps = await app_service.create_batch(
            db_session, ApplicationBatchCreate(job_ids=[job.id]), UID
        )

        assert apps and all(a.user_id == UID for a in apps)
        row = await _read_unscoped(db_session, apps[0].id)
        assert row.user_id == UID
