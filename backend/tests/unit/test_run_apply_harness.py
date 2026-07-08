"""Phase 2/3: run_apply harness wiring — trajectory persistence, review enqueue, review task.

The browser is fully mocked (build_apply_agent returns a fake agent whose run() yields a
FakeHistory); this exercises the orchestration/observation/enqueue path without a browser.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.automation.runtime import apply as apply_mod
from app.core.harness import record
from app.models.application import Application
from app.models.harness import RunTrajectory
from app.models.job import Job
from app.models.resume import Resume
from app.models.user import User
from app.workers import tasks
from tests.conftest import TEST_USER_ID
from tests.unit.test_observe import FakeHistory


async def _seed_app(db) -> Application:
    db.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
    job = Job(
        user_id=TEST_USER_ID, platform="linkedin", platform_job_id="j1",
        title="t", company="c", url="https://x",
    )
    db.add(job)
    await db.flush()
    resume = Resume(
        user_id=TEST_USER_ID, name="r", type="base", template_id="modern",
        file_path_pdf="/tmp/r.pdf",
    )
    db.add(resume)
    await db.flush()
    app = Application(
        user_id=TEST_USER_ID, job_id=job.id, resume_id=resume.id,
        status="applying", apply_mode="autonomous",
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    return app


class _SessionCM:
    """Async-context-manager stand-in that yields the test session (for the dedicated
    observability session opened inside _record_and_review)."""

    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


def _mock_browser(db, history=None, *, run_side_effect=None):
    """Patch the browser-use seams so run_apply drives a fake agent, and route the
    dedicated trajectory session back to the test session so it's observable."""
    store = MagicMock()
    store.load_session_cookies = AsyncMock(return_value={"cookies": [], "origins": []})
    store.get_llm_key = AsyncMock(return_value="sk-test")
    fake_agent = MagicMock()
    if run_side_effect is not None:
        fake_agent.run = AsyncMock(side_effect=run_side_effect)
    else:
        fake_agent.run = AsyncMock(return_value=history)
    # The resume is materialized from storage to a temp path for the browser.
    storage_service = MagicMock(
        return_value=MagicMock(materialize_to_temp=AsyncMock(return_value="/tmp/resume.pdf"))
    )
    return patch.multiple(
        apply_mod,
        CredentialStore=MagicMock(return_value=store),
        build_browser_profile=MagicMock(return_value=MagicMock()),
        build_apply_llm=MagicMock(return_value=MagicMock()),
        build_apply_agent=MagicMock(return_value=fake_agent),
        StorageService=storage_service,
        async_session_factory=lambda: _SessionCM(db),
    )


class _RaisingStructured(FakeHistory):
    """A history whose structured_output property raises (malformed agent done-text)."""

    @property
    def structured_output(self):
        raise ValueError("agent done-text is not valid ApplicationResult JSON")


class TestRunApplyHarness:
    async def test_persists_trajectory_and_enqueues_review(self, db_session):
        app = await _seed_app(db_session)
        history = FakeHistory(actions=["go_to_url", "done"], urls=["https://x/job"])
        redis = MagicMock()
        redis.enqueue_job = AsyncMock()

        with _mock_browser(db_session, history):
            result = await apply_mod.run_apply(db_session, app, redis=redis)

        assert result.submitted is True
        trajs = (
            await db_session.execute(
                select(RunTrajectory).where(RunTrajectory.application_id == app.id)
            )
        ).scalars().all()
        assert len(trajs) == 1
        redis.enqueue_job.assert_awaited_once()
        call = redis.enqueue_job.await_args
        assert call.args[0] == "review_application_run"
        assert call.args[1] == trajs[0].id

    async def test_no_redis_persists_trajectory_but_skips_review(self, db_session):
        app = await _seed_app(db_session)
        with _mock_browser(db_session, FakeHistory()):
            await apply_mod.run_apply(db_session, app, redis=None)
        trajs = (
            await db_session.execute(
                select(RunTrajectory).where(RunTrajectory.application_id == app.id)
            )
        ).scalars().all()
        assert len(trajs) == 1

    async def test_malformed_structured_output_does_not_abort(self, db_session):
        """A raising structured_output property must fall back, not crash + skip recording."""
        app = await _seed_app(db_session)
        with _mock_browser(db_session, _RaisingStructured(final="Submitted, confirmation #42")):
            result = await apply_mod.run_apply(db_session, app, redis=None)
        assert result.submitted is True  # fell back to final_result()
        trajs = (
            await db_session.execute(
                select(RunTrajectory).where(RunTrajectory.application_id == app.id)
            )
        ).scalars().all()
        assert len(trajs) == 1  # trajectory still persisted

    async def test_run_failure_records_failed_trajectory_and_reraises(self, db_session):
        """When agent.run raises, the harness must still record + review, then re-raise."""
        app = await _seed_app(db_session)
        redis = MagicMock()
        redis.enqueue_job = AsyncMock()

        with _mock_browser(db_session, run_side_effect=RuntimeError("CDP Connection refused")):
            with pytest.raises(RuntimeError, match="Connection refused"):
                await apply_mod.run_apply(db_session, app, redis=redis)

        trajs = (
            await db_session.execute(
                select(RunTrajectory).where(RunTrajectory.application_id == app.id)
            )
        ).scalars().all()
        assert len(trajs) == 1 and trajs[0].status == "failed"
        redis.enqueue_job.assert_awaited_once()
        signals = redis.enqueue_job.await_args.args[2]
        assert any("Connection refused" in e for e in signals["errors"])


class TestReviewTask:
    async def test_loads_trajectory_and_runs_review(self, db_session):
        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db_session.commit()
        traj = await record.record_trajectory(
            db_session, user_id=TEST_USER_ID, application_id="app1",
            platform="linkedin", status="completed",
        )

        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=db_session)
        session_cm.__aexit__ = AsyncMock(return_value=False)

        with patch.object(tasks, "async_session_factory", return_value=session_cm), patch.object(
            tasks, "build_llm_client_for_user", new=AsyncMock(return_value=MagicMock())
        ), patch.object(
            tasks, "review_run",
            new=AsyncMock(return_value={"verdict": "success", "failure_class": None, "skill_id": None}),
        ) as review:
            await tasks.review_application_run({"redis": None}, traj.id, {"final_url": "x"})

        review.assert_awaited_once()
        assert review.await_args.args[2].id == traj.id

    async def test_missing_trajectory_is_noop(self, db_session):
        session_cm = MagicMock()
        session_cm.__aenter__ = AsyncMock(return_value=db_session)
        session_cm.__aexit__ = AsyncMock(return_value=False)
        with patch.object(tasks, "async_session_factory", return_value=session_cm), patch.object(
            tasks, "review_run", new=AsyncMock()
        ) as review:
            await tasks.review_application_run({"redis": None}, "nonexistent-id")
        review.assert_not_awaited()
