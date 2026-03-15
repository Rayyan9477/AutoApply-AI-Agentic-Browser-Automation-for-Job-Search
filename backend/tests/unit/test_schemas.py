"""Unit tests for all Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.analytics import (
    AnalyticsResponse,
    ATSScoreDistribution,
    DashboardStats,
    LLMUsageStats,
)
from app.schemas.application import (
    ApplicationBatchCreate,
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationStatusUpdate,
)
from app.schemas.job import JobListingResponse, JobListResponse, JobSearchRequest
from app.schemas.resume import (
    ResumeGenerateRequest,
    ResumeScoreResponse,
    ResumeUploadResponse,
)
from app.schemas.settings import LLMProviderStatus, SettingsUpdate

# ---------------------------------------------------------------------------
# JobSearchRequest
# ---------------------------------------------------------------------------


class TestJobSearchRequest:
    def test_defaults(self):
        req = JobSearchRequest(query="python developer")
        assert req.query == "python developer"
        assert req.location == ""
        assert req.platforms == ["linkedin", "indeed", "glassdoor"]
        assert req.filters == {}
        assert req.limit == 20

    def test_all_fields(self):
        req = JobSearchRequest(
            query="backend engineer",
            location="NYC",
            platforms=["linkedin"],
            filters={"remote": True},
            limit=50,
        )
        assert req.location == "NYC"
        assert req.platforms == ["linkedin"]
        assert req.filters == {"remote": True}
        assert req.limit == 50

    def test_limit_ge_1(self):
        with pytest.raises(ValidationError):
            JobSearchRequest(query="test", limit=0)

    def test_limit_le_100(self):
        with pytest.raises(ValidationError):
            JobSearchRequest(query="test", limit=101)

    def test_query_min_length(self):
        with pytest.raises(ValidationError):
            JobSearchRequest(query="")

    def test_query_required(self):
        with pytest.raises(ValidationError):
            JobSearchRequest()


# ---------------------------------------------------------------------------
# JobListingResponse
# ---------------------------------------------------------------------------


class TestJobListingResponse:
    def test_model_validate_from_dict(self):
        data = {
            "id": "abc123",
            "platform": "linkedin",
            "platform_job_id": "job-1",
            "title": "Dev",
            "company": "Acme",
            "location": "Remote",
            "url": "https://example.com",
            "description": "desc",
            "status": "new",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
        }
        resp = JobListingResponse.model_validate(data)
        assert resp.id == "abc123"
        assert resp.remote is False
        assert resp.salary_range is None

    def test_optional_fields(self):
        data = {
            "id": "abc123",
            "platform": "indeed",
            "platform_job_id": "job-2",
            "title": "Engineer",
            "company": "Corp",
            "location": "NYC",
            "url": "https://example.com",
            "description": "desc",
            "status": "saved",
            "created_at": "2025-01-01T00:00:00",
            "updated_at": "2025-01-01T00:00:00",
            "salary_range": "$100k-$150k",
            "remote": True,
            "match_score": 0.92,
        }
        resp = JobListingResponse.model_validate(data)
        assert resp.salary_range == "$100k-$150k"
        assert resp.remote is True
        assert resp.match_score == 0.92


# ---------------------------------------------------------------------------
# JobListResponse
# ---------------------------------------------------------------------------


class TestJobListResponse:
    def test_with_items_and_pagination(self):
        resp = JobListResponse(items=[], total=0, page=1, page_size=20, has_next=False)
        assert resp.items == []
        assert resp.total == 0
        assert resp.has_next is False

    def test_has_next_true(self):
        resp = JobListResponse(items=[], total=50, page=1, page_size=20, has_next=True)
        assert resp.has_next is True


# ---------------------------------------------------------------------------
# ApplicationCreate
# ---------------------------------------------------------------------------


class TestApplicationCreate:
    def test_defaults(self):
        app = ApplicationCreate(job_id="job1")
        assert app.job_id == "job1"
        assert app.resume_id is None
        assert app.apply_mode == "review"

    def test_explicit_fields(self):
        app = ApplicationCreate(job_id="job1", resume_id="res1", apply_mode="autonomous")
        assert app.resume_id == "res1"
        assert app.apply_mode == "autonomous"


# ---------------------------------------------------------------------------
# ApplicationBatchCreate
# ---------------------------------------------------------------------------


class TestApplicationBatchCreate:
    def test_valid_batch(self):
        batch = ApplicationBatchCreate(job_ids=["j1", "j2"])
        assert len(batch.job_ids) == 2

    def test_min_length_validation(self):
        with pytest.raises(ValidationError):
            ApplicationBatchCreate(job_ids=[])


# ---------------------------------------------------------------------------
# ApplicationStatusUpdate
# ---------------------------------------------------------------------------


class TestApplicationStatusUpdate:
    def test_with_status_only(self):
        update = ApplicationStatusUpdate(status="applied")
        assert update.status == "applied"
        assert update.notes is None

    def test_with_notes(self):
        update = ApplicationStatusUpdate(status="rejected", notes="Not a fit")
        assert update.notes == "Not a fit"


# ---------------------------------------------------------------------------
# ApplicationListResponse
# ---------------------------------------------------------------------------


class TestApplicationListResponse:
    def test_pagination_fields(self):
        resp = ApplicationListResponse(
            items=[], total=5, page=1, page_size=20, has_next=False
        )
        assert resp.total == 5
        assert resp.page == 1
        assert resp.page_size == 20
        assert resp.has_next is False


# ---------------------------------------------------------------------------
# ResumeGenerateRequest
# ---------------------------------------------------------------------------


class TestResumeGenerateRequest:
    def test_defaults(self):
        req = ResumeGenerateRequest(base_resume_id="r1", job_id="j1")
        assert req.template_id == "modern"
        assert req.output_formats == ["pdf", "docx"]

    def test_custom_values(self):
        req = ResumeGenerateRequest(
            base_resume_id="r1",
            job_id="j1",
            template_id="classic",
            output_formats=["pdf"],
        )
        assert req.template_id == "classic"
        assert req.output_formats == ["pdf"]


# ---------------------------------------------------------------------------
# ResumeScoreResponse
# ---------------------------------------------------------------------------


class TestResumeScoreResponse:
    def test_all_score_fields_present(self):
        resp = ResumeScoreResponse(
            resume_id="r1",
            job_id="j1",
            overall_score=0.8,
            skill_score=0.9,
            experience_score=0.7,
            education_score=0.6,
            keyword_score=0.5,
        )
        assert resp.overall_score == 0.8
        assert resp.skill_score == 0.9
        assert resp.experience_score == 0.7
        assert resp.education_score == 0.6
        assert resp.keyword_score == 0.5
        assert resp.missing_skills == []
        assert resp.suggestions == []


# ---------------------------------------------------------------------------
# ResumeUploadResponse
# ---------------------------------------------------------------------------


class TestResumeUploadResponse:
    def test_required_fields(self):
        resp = ResumeUploadResponse(
            id="r1", name="my_resume.pdf", file_format="pdf", word_count=500
        )
        assert resp.id == "r1"
        assert resp.name == "my_resume.pdf"
        assert resp.file_format == "pdf"
        assert resp.word_count == 500
        assert resp.skills_detected == []

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            ResumeUploadResponse(id="r1", name="my_resume.pdf", file_format="pdf")


# ---------------------------------------------------------------------------
# DashboardStats
# ---------------------------------------------------------------------------


class TestDashboardStats:
    def test_all_defaults_are_zero(self):
        stats = DashboardStats()
        assert stats.total_jobs_found == 0
        assert stats.total_applications == 0
        assert stats.applications_pending == 0
        assert stats.applications_applied == 0
        assert stats.applications_interview == 0
        assert stats.applications_rejected == 0
        assert stats.applications_offer == 0
        assert stats.avg_ats_score == 0.0
        assert stats.total_llm_cost_usd == 0.0


# ---------------------------------------------------------------------------
# AnalyticsResponse
# ---------------------------------------------------------------------------


class TestAnalyticsResponse:
    def test_nested_model_construction(self):
        stats = DashboardStats(total_jobs_found=10, total_applications=5)
        resp = AnalyticsResponse(stats=stats)
        assert resp.stats.total_jobs_found == 10
        assert resp.funnel == []
        assert resp.ats_distribution == []
        assert resp.llm_usage == []
        assert resp.timeline == []


# ---------------------------------------------------------------------------
# ATSScoreDistribution
# ---------------------------------------------------------------------------


class TestATSScoreDistribution:
    def test_required_fields(self):
        dist = ATSScoreDistribution(range_label="80-100", count=5)
        assert dist.range_label == "80-100"
        assert dist.count == 5

    def test_missing_field_raises(self):
        with pytest.raises(ValidationError):
            ATSScoreDistribution(range_label="0-20")


# ---------------------------------------------------------------------------
# LLMUsageStats
# ---------------------------------------------------------------------------


class TestLLMUsageStats:
    def test_required_fields(self):
        usage = LLMUsageStats(provider="openai", model="gpt-4")
        assert usage.provider == "openai"
        assert usage.model == "gpt-4"
        assert usage.total_requests == 0
        assert usage.total_tokens == 0
        assert usage.total_cost_usd == 0.0
        assert usage.avg_latency_ms == 0.0


# ---------------------------------------------------------------------------
# SettingsUpdate
# ---------------------------------------------------------------------------


class TestSettingsUpdate:
    def test_partial_update_all_optional(self):
        update = SettingsUpdate()
        assert update.apply_mode is None
        assert update.min_ats_score is None
        assert update.max_parallel is None
        assert update.platforms_enabled is None
        assert update.candidate_profile is None

    def test_single_field_update(self):
        update = SettingsUpdate(apply_mode="autonomous")
        assert update.apply_mode == "autonomous"

    def test_min_ats_score_ge_0(self):
        with pytest.raises(ValidationError):
            SettingsUpdate(min_ats_score=-0.1)

    def test_min_ats_score_le_1(self):
        with pytest.raises(ValidationError):
            SettingsUpdate(min_ats_score=1.1)

    def test_min_ats_score_valid_bounds(self):
        assert SettingsUpdate(min_ats_score=0.0).min_ats_score == 0.0
        assert SettingsUpdate(min_ats_score=1.0).min_ats_score == 1.0

    def test_max_parallel_ge_1(self):
        with pytest.raises(ValidationError):
            SettingsUpdate(max_parallel=0)

    def test_max_parallel_le_5(self):
        with pytest.raises(ValidationError):
            SettingsUpdate(max_parallel=6)

    def test_max_parallel_valid_bounds(self):
        assert SettingsUpdate(max_parallel=1).max_parallel == 1
        assert SettingsUpdate(max_parallel=5).max_parallel == 5


# ---------------------------------------------------------------------------
# LLMProviderStatus
# ---------------------------------------------------------------------------


class TestLLMProviderStatus:
    def test_defaults(self):
        status = LLMProviderStatus(provider="openai")
        assert status.provider == "openai"
        assert status.configured is False
        assert status.model == ""
        assert status.is_primary is False

    def test_configured_provider(self):
        status = LLMProviderStatus(
            provider="anthropic", configured=True, model="claude-3", is_primary=True
        )
        assert status.configured is True
        assert status.model == "claude-3"
        assert status.is_primary is True
