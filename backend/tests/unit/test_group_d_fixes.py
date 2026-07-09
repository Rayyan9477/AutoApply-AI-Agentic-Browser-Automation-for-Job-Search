"""Group D remediation regression tests: anomaly monitor task, skill-feedback loop,
SystemIssue admin endpoint."""

from unittest.mock import patch

from sqlalchemy import select

from app.core.harness import record
from app.core.harness.skills import record_skill
from app.models.application import Application
from app.models.enums import ApplicationStatus, ApplyMode, RunVerdictResult, SkillStatus
from app.models.harness import DomainSkill, SystemIssue
from app.models.job import Job
from app.models.user import User
from app.workers import tasks
from tests.conftest import TEST_USER_ID


class _SessionCM:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


# --- D1: scheduled anomaly monitor persists SystemIssue ----------------------


class TestAnomalyMonitor:
    async def test_monitor_persists_issue_on_high_failure_rate(self, db_session):
        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        for i in range(6):
            job = Job(
                user_id=TEST_USER_ID, platform="linkedin", platform_job_id=f"j{i}",
                title="t", company="c", url="https://x",
            )
            db_session.add(job)
            await db_session.flush()
            status = ApplicationStatus.FAILED if i < 4 else ApplicationStatus.APPLIED
            db_session.add(
                Application(
                    user_id=TEST_USER_ID, job_id=job.id, status=status,
                    apply_mode=ApplyMode.AUTONOMOUS,
                )
            )
        await db_session.commit()

        with patch.object(tasks, "async_session_factory", lambda: _SessionCM(db_session)):
            await tasks.monitor_system_health({"redis": None})

        issues = (await db_session.execute(select(SystemIssue))).scalars().all()
        assert any(i.category == "apply_failure_rate" for i in issues)


# --- D2: verdict feeds back into skill scoring ------------------------------


class TestSkillFeedbackLoop:
    async def _skill_and_traj(self, db_session):
        skill = await record_skill(db_session, "linkedin", "Easy Apply at .jobs-apply-button")
        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db_session.commit()
        traj = await record.record_trajectory(
            db_session, user_id=TEST_USER_ID, application_id="app-1",
            platform="linkedin", skills_used=[skill.id],
        )
        return skill, traj

    async def test_success_verdict_increments_skill_score(self, db_session):
        skill, traj = await self._skill_and_traj(db_session)
        await tasks._score_skills_from_verdict(db_session, traj, RunVerdictResult.SUCCESS)
        refreshed = await db_session.get(DomainSkill, skill.id)
        assert refreshed.score == 1

    async def test_failure_verdict_decrements_skill_score(self, db_session):
        skill, traj = await self._skill_and_traj(db_session)
        await tasks._score_skills_from_verdict(db_session, traj, RunVerdictResult.FAILED)
        refreshed = await db_session.get(DomainSkill, skill.id)
        assert refreshed.score == -1

    async def test_repeated_failures_auto_retire(self, db_session):
        skill, traj = await self._skill_and_traj(db_session)
        for _ in range(3):
            await tasks._score_skills_from_verdict(db_session, traj, RunVerdictResult.FAILED)
        refreshed = await db_session.get(DomainSkill, skill.id)
        assert refreshed.status == SkillStatus.RETIRED  # score <= -3 auto-retires


# --- D3: SystemIssue admin endpoint (superuser-guarded) ---------------------


class TestAdminSystemIssues:
    async def test_non_superuser_forbidden(self, anon_client):
        await anon_client.post(
            "/api/v1/auth/register", json={"email": "u@x.com", "password": "password123"}
        )
        token = (
            await anon_client.post(
                "/api/v1/auth/login", data={"username": "u@x.com", "password": "password123"}
            )
        ).json()["access_token"]
        r = await anon_client.get(
            "/api/v1/admin/system-issues", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 403

    async def test_superuser_allowed(self, anon_client, db_session):
        await anon_client.post(
            "/api/v1/auth/register", json={"email": "admin@x.com", "password": "password123"}
        )
        user = (
            await db_session.execute(select(User).where(User.email == "admin@x.com"))
        ).scalar_one()
        user.is_superuser = True
        await db_session.commit()

        token = (
            await anon_client.post(
                "/api/v1/auth/login", data={"username": "admin@x.com", "password": "password123"}
            )
        ).json()["access_token"]
        r = await anon_client.get(
            "/api/v1/admin/system-issues", headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 200
        assert r.json() == []
