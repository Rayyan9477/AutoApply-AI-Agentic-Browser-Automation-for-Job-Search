"""Phase 3: harness diagnosis taxonomy, skill registry, anomaly detection, review loop."""

from unittest.mock import AsyncMock

from sqlalchemy import select

from app.core.harness import record, review
from app.core.harness.anomaly import detect_anomalies
from app.core.harness.diagnose import diagnose
from app.core.harness.distil import DistilledSkill
from app.core.harness.judge import JudgeOutput
from app.core.harness.skills import (
    add_feedback,
    build_skill_guidance,
    load_skills,
    pii_clean,
    record_skill,
)
from app.models.application import Application
from app.models.enums import (
    ApplicationStatus,
    ApplyMode,
    FailureClass,
    RunVerdictResult,
    SkillStatus,
)
from app.models.harness import RunDiagnosis, RunVerdict
from app.models.job import Job
from app.models.user import User
from tests.conftest import TEST_USER_ID


class TestDiagnose:
    def test_timeout(self):
        assert diagnose({"timed_out": True}).failure_class == FailureClass.TIMEOUT

    def test_captcha(self):
        d = diagnose({"errors": ["Please verify you are human (CAPTCHA)"]})
        assert d.failure_class == FailureClass.CAPTCHA_WALL

    def test_session_from_url(self):
        d = diagnose({"final_url": "https://www.linkedin.com/login"})
        assert d.failure_class == FailureClass.SESSION_EXPIRED

    def test_loop(self):
        assert diagnose({"loop_detected": True}).failure_class == FailureClass.LOOP

    def test_dom_drift(self):
        d = diagnose({"errors": ["element not found: #apply-button"]})
        assert d.failure_class == FailureClass.DOM_DRIFT

    def test_offtrack(self):
        assert diagnose({"consecutive_failures": 4}).failure_class == FailureClass.AGENT_OFFTRACK

    def test_unknown(self):
        assert diagnose({}).failure_class == FailureClass.UNKNOWN


class TestPiiGate:
    def test_clean_content_passes(self):
        assert pii_clean("On LinkedIn, build search URLs directly; never type in the homepage box.")

    def test_email_rejected(self):
        assert not pii_clean("Use login jane@example.com to apply")

    def test_token_rejected(self):
        assert not pii_clean("api key sk-abcdef0123456789")


class TestSkillRegistry:
    async def test_record_versions_and_pii_gate(self, db_session):
        s1 = await record_skill(db_session, "linkedin", "Easy Apply lives at .jobs-apply-button")
        assert s1 is not None and s1.version == 1
        s2 = await record_skill(db_session, "linkedin", "Pagination reloads the page")
        assert s2 is not None and s2.version == 2
        rejected = await record_skill(db_session, "linkedin", "contact me at a@b.com")
        assert rejected is None

    async def test_feedback_auto_retires(self, db_session):
        skill = await record_skill(db_session, "indeed", "Indeed jobs have data-jk attributes")
        assert skill is not None
        updated = await add_feedback(db_session, skill.id, -3, reason="stale selector")
        assert updated is not None
        assert updated.status == SkillStatus.RETIRED

    async def test_load_skills_active_and_ranked(self, db_session):
        low = await record_skill(db_session, "glassdoor", "low-value note")
        high = await record_skill(db_session, "glassdoor", "high-value note")
        await add_feedback(db_session, high.id, 2)
        await add_feedback(db_session, low.id, -3)  # retired
        loaded = await load_skills(db_session, "glassdoor")
        assert [s.id for s in loaded] == [high.id]  # retired one excluded


class TestSkillGuidance:
    async def test_empty_returns_blank(self, db_session):
        assert build_skill_guidance([]) == ""

    async def test_renders_skill_content(self, db_session):
        s1 = await record_skill(db_session, "linkedin", "Easy Apply is at .jobs-apply-button")
        s2 = await record_skill(db_session, "linkedin", "Pagination reloads the page")
        guidance = build_skill_guidance([s1, s2])
        assert "Easy Apply is at .jobs-apply-button" in guidance
        assert "Pagination reloads the page" in guidance
        assert guidance.startswith("Learned guidance")


class TestAnomalyDetection:
    async def _seed_apps(self, db, *, total: int, failed: int) -> None:
        db.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        for i in range(total):
            job = Job(
                user_id=TEST_USER_ID, platform="linkedin", platform_job_id=f"j{i}",
                title="t", company="c", url="https://x",
            )
            db.add(job)
            await db.flush()
            status = ApplicationStatus.FAILED if i < failed else ApplicationStatus.APPLIED
            db.add(
                Application(
                    user_id=TEST_USER_ID, job_id=job.id, status=status, apply_mode=ApplyMode.AUTONOMOUS
                )
            )
        await db.commit()

    async def test_high_failure_rate_raises_issue(self, db_session):
        await self._seed_apps(db_session, total=6, failed=4)
        issues = await detect_anomalies(db_session)
        assert any(i.category == "apply_failure_rate" for i in issues)

    async def test_healthy_no_issue(self, db_session):
        await self._seed_apps(db_session, total=6, failed=0)
        issues = await detect_anomalies(db_session)
        assert all(i.category != "apply_failure_rate" for i in issues)


class TestReviewOrchestrator:
    async def _trajectory(self, db):
        db.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db.commit()
        return await record.record_trajectory(
            db, user_id=TEST_USER_ID, application_id="app-1", platform="linkedin",
            agent_self_report="I submitted the application", status="completed",
        )

    async def test_failed_run_judged_diagnosed_and_skill_saved(self, db_session):
        traj = await self._trajectory(db_session)
        llm = AsyncMock()
        llm.complete_with_structured_output = AsyncMock(
            side_effect=[
                JudgeOutput(verdict=RunVerdictResult.FAILED, confidence=0.9, reason="login wall"),
                DistilledSkill(worth_saving=True, content="Easy Apply is at .jobs-apply-button"),
            ]
        )

        result = await review.review_run(
            db_session, llm, traj, signals={"final_url": "https://linkedin.com/login"}
        )

        assert result["verdict"] == RunVerdictResult.FAILED
        assert result["failure_class"] == FailureClass.SESSION_EXPIRED
        assert result["skill_id"] is not None
        verdicts = (
            await db_session.execute(select(RunVerdict).where(RunVerdict.run_id == traj.id))
        ).scalars().all()
        diags = (
            await db_session.execute(select(RunDiagnosis).where(RunDiagnosis.run_id == traj.id))
        ).scalars().all()
        assert len(verdicts) == 1 and len(diags) == 1

    async def test_success_run_no_diagnosis_no_skill(self, db_session):
        traj = await self._trajectory(db_session)
        llm = AsyncMock()
        llm.complete_with_structured_output = AsyncMock(
            side_effect=[
                JudgeOutput(verdict=RunVerdictResult.SUCCESS, confidence=0.95, reason="confirmed"),
                DistilledSkill(worth_saving=False, content=""),
            ]
        )

        result = await review.review_run(db_session, llm, traj, signals={})

        assert result["verdict"] == RunVerdictResult.SUCCESS
        assert result["failure_class"] is None
        assert result["skill_id"] is None
        diags = (
            await db_session.execute(select(RunDiagnosis).where(RunDiagnosis.run_id == traj.id))
        ).scalars().all()
        assert len(diags) == 0
