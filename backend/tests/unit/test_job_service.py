"""Unit tests for the job search service."""

from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions import RecordNotFoundError
from app.models.job import Job
from app.schemas.job import JobSearchRequest
from app.services import job_search


def _fix_job_data(sample_job_data: dict) -> dict:
    """Convert skills_required from list to dict for schema compatibility."""
    data = {**sample_job_data}
    if isinstance(data.get("skills_required"), list):
        data["skills_required"] = {"skills": data["skills_required"]}
    return data


class TestSearchJobs:
    async def test_search_jobs_returns_empty_when_no_platforms(
        self, db_session,
    ):
        """Search should return empty results when platforms produce nothing."""
        request = JobSearchRequest(
            query="python developer", platforms=[],
        )
        with patch.object(
            job_search.platform_registry,
            "list_platforms",
            return_value=[],
        ):
            result = await job_search.search_jobs(db_session, request)
        assert result.items == []
        assert result.total == 0
        assert result.page == 1
        assert result.has_next is False

    async def test_search_jobs_collects_platform_results(self, db_session):
        """Search should collect results from platform scrapers."""
        from app.core.automation.platforms.base import JobListing

        mock_listing = JobListing(
            platform="linkedin",
            platform_job_id="ext-999",
            title="Python Dev",
            company="TestCo",
            location="Remote",
            url="https://example.com/job/999",
            description="A Python role",
        )
        mock_platform = AsyncMock()
        mock_platform.search = AsyncMock(return_value=[mock_listing])

        request = JobSearchRequest(
            query="python developer", platforms=["linkedin"],
        )

        with (
            patch.object(
                job_search.platform_registry, "has", return_value=True,
            ),
            patch.object(
                job_search.platform_registry,
                "create",
                return_value=mock_platform,
            ),
        ):
            result = await job_search.search_jobs(db_session, request)

        assert result.total == 1
        assert result.items[0].title == "Python Dev"
        assert result.items[0].platform == "linkedin"

    async def test_search_jobs_handles_platform_failure(self, db_session):
        """Search should return empty results when platform raises."""
        mock_platform = AsyncMock()
        mock_platform.search = AsyncMock(
            side_effect=RuntimeError("network error"),
        )

        request = JobSearchRequest(
            query="python developer", platforms=["linkedin"],
        )

        with (
            patch.object(
                job_search.platform_registry, "has", return_value=True,
            ),
            patch.object(
                job_search.platform_registry,
                "create",
                return_value=mock_platform,
            ),
        ):
            result = await job_search.search_jobs(db_session, request)

        assert result.total == 0
        assert result.items == []


class TestListJobs:
    async def test_list_jobs_empty_db(self, db_session):
        result = await job_search.list_jobs(db_session)
        assert result.items == []
        assert result.total == 0
        assert result.has_next is False

    async def test_list_jobs_with_data(self, db_session, sample_job_data):
        fixed = _fix_job_data(sample_job_data)
        for i in range(3):
            data = {**fixed, "platform_job_id": f"job-{i}"}
            db_session.add(Job(**data))
        await db_session.commit()

        result = await job_search.list_jobs(db_session, page=1, page_size=2)
        assert len(result.items) == 2
        assert result.total == 3
        assert result.has_next is True

        result2 = await job_search.list_jobs(db_session, page=2, page_size=2)
        assert len(result2.items) == 1
        assert result2.has_next is False

    async def test_list_jobs_filter_by_status(
        self, db_session, sample_job_data,
    ):
        fixed = _fix_job_data(sample_job_data)
        for i, status in enumerate(["new", "new", "saved"]):
            data = {
                **fixed, "platform_job_id": f"job-{i}", "status": status,
            }
            db_session.add(Job(**data))
        await db_session.commit()

        result = await job_search.list_jobs(db_session, status="new")
        assert result.total == 2

        result_saved = await job_search.list_jobs(db_session, status="saved")
        assert result_saved.total == 1


class TestGetJob:
    async def test_get_job_found(self, db_session, sample_job_data):
        job = Job(**sample_job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        found = await job_search.get_job(db_session, job.id)
        assert found.id == job.id
        assert found.title == sample_job_data["title"]

    async def test_get_job_not_found_raises(self, db_session):
        with pytest.raises(RecordNotFoundError):
            await job_search.get_job(db_session, "nonexistent_id")


class TestDeleteJob:
    async def test_delete_job_success(self, db_session, sample_job_data):
        job = Job(**sample_job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        await job_search.delete_job(db_session, job.id)

        with pytest.raises(RecordNotFoundError):
            await job_search.get_job(db_session, job.id)

    async def test_delete_job_not_found_raises(self, db_session):
        with pytest.raises(RecordNotFoundError):
            await job_search.delete_job(db_session, "nonexistent_id")


class TestAnalyzeJob:
    async def test_analyze_job_no_resume_returns_placeholder(
        self, db_session, sample_job_data,
    ):
        """Without a resume_id, analyze_job returns zero scores."""
        job = Job(**sample_job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        result = await job_search.analyze_job(db_session, job.id)
        assert result.job_id == job.id
        assert result.match_score == 0.0
        assert result.skill_match == 0.0
        assert result.keyword_match == 0.0
        assert len(result.suggestions) > 0

    async def test_analyze_job_not_found_raises(self, db_session):
        with pytest.raises(RecordNotFoundError):
            await job_search.analyze_job(db_session, "nonexistent_id")
