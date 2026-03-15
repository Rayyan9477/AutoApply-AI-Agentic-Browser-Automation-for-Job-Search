"""Unit tests for the analytics service."""

from app.config.constants import ApplicationStatus
from app.models.application import Application
from app.models.job import Job
from app.services import analytics


async def _create_job(db_session, sample_job_data, suffix="0"):
    data = {**sample_job_data, "platform_job_id": f"job-{suffix}"}
    job = Job(**data)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


async def _create_application(db_session, job_id, status, ats_score=None):
    app = Application(
        job_id=job_id,
        status=status,
        apply_mode="review",
        ats_score=ats_score,
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)
    return app


class TestGetDashboardStats:
    async def test_dashboard_stats_empty_db(self, db_session):
        stats = await analytics.get_dashboard_stats(db_session)
        assert stats.total_jobs_found == 0
        assert stats.total_applications == 0
        assert stats.applications_pending == 0
        assert stats.applications_applied == 0
        assert stats.applications_interview == 0
        assert stats.applications_rejected == 0
        assert stats.applications_offer == 0
        assert stats.avg_ats_score == 0.0

    async def test_dashboard_stats_with_data(self, db_session, sample_job_data):
        job = await _create_job(db_session, sample_job_data)

        await _create_application(db_session, job.id, ApplicationStatus.PENDING_REVIEW)
        await _create_application(db_session, job.id, ApplicationStatus.APPLIED)
        await _create_application(db_session, job.id, ApplicationStatus.APPLIED)
        await _create_application(db_session, job.id, ApplicationStatus.INTERVIEW)
        await _create_application(db_session, job.id, ApplicationStatus.REJECTED)

        stats = await analytics.get_dashboard_stats(db_session)
        assert stats.total_jobs_found == 1
        assert stats.total_applications == 5
        assert stats.applications_pending == 1
        assert stats.applications_applied == 2
        assert stats.applications_interview == 1
        assert stats.applications_rejected == 1
        assert stats.applications_offer == 0


class TestGetFunnel:
    async def test_funnel_returns_all_stages(self, db_session):
        funnel = await analytics.get_funnel(db_session)
        assert len(funnel) == 9
        stage_names = [f.stage for f in funnel]
        assert ApplicationStatus.QUEUED in stage_names
        assert ApplicationStatus.APPLIED in stage_names
        assert ApplicationStatus.WITHDRAWN in stage_names
        # All counts should be 0 on empty DB
        for entry in funnel:
            assert entry.count == 0


class TestGetAtsDistribution:
    async def test_ats_distribution_returns_buckets(self, db_session):
        distribution = await analytics.get_ats_distribution(db_session)
        assert len(distribution) == 5
        labels = [d.range_label for d in distribution]
        assert "0-20" in labels
        assert "80-100" in labels


class TestGetLlmUsage:
    async def test_llm_usage_returns_empty(self, db_session):
        result = await analytics.get_llm_usage(db_session)
        assert result == []
