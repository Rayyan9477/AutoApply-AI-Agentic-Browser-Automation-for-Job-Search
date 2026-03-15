"""Unit tests for app.core.ats.experience_analyzer.ExperienceAnalyzer."""

from __future__ import annotations

import pytest

from app.core.ats.experience_analyzer import ExperienceAnalyzer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def analyzer() -> ExperienceAnalyzer:
    return ExperienceAnalyzer(nlp=None)


@pytest.fixture()
def sample_experience() -> list[dict]:
    return [
        {
            "title": "Senior Software Engineer",
            "company": "TechCo",
            "duration_years": 3,
            "description": "Led backend development, code review, and mentoring.",
            "responsibilities": ["architect microservices", "deploy releases"],
        },
        {
            "title": "Software Engineer",
            "company": "StartupInc",
            "duration_years": 2,
            "description": "Built REST APIs and collaborated with frontend team.",
            "responsibilities": ["troubleshoot issues", "coordinate with stakeholders"],
        },
    ]


@pytest.fixture()
def job_description() -> str:
    return (
        "We are looking for a Senior Software Engineer with 5+ years of experience. "
        "You will architect systems, collaborate cross-functionally, "
        "troubleshoot production issues, and deliver new features."
    )


# ---------------------------------------------------------------------------
# analyze_experience
# ---------------------------------------------------------------------------


class TestAnalyzeExperience:
    def test_returns_score_and_details(self, analyzer, sample_experience, job_description):
        score, details = analyzer.analyze_experience(
            sample_experience, job_description, {}
        )
        assert isinstance(score, float)
        assert isinstance(details, list)

    def test_score_between_zero_and_one(self, analyzer, sample_experience, job_description):
        score, _ = analyzer.analyze_experience(
            sample_experience, job_description, {}
        )
        assert 0.0 <= score <= 1.0

    def test_empty_experience_returns_zero(self, analyzer, job_description):
        score, details = analyzer.analyze_experience([], job_description, {})
        assert score == 0.0
        assert details == []

    def test_metadata_required_years_used(self, analyzer, sample_experience):
        score, _ = analyzer.analyze_experience(
            sample_experience, "some job", {"required_years": 5}
        )
        # 5 total years / 5 required = 1.0 for years component
        assert score > 0.0


# ---------------------------------------------------------------------------
# _extract_required_years
# ---------------------------------------------------------------------------


class TestExtractRequiredYears:
    def test_extracts_from_plus_years(self, analyzer):
        years = analyzer._extract_required_years("5+ years of experience required", {})
        assert years == 5.0

    def test_extracts_from_minimum_pattern(self, analyzer):
        years = analyzer._extract_required_years("minimum 3 years experience", {})
        assert years == 3.0

    def test_extracts_from_range_pattern(self, analyzer):
        years = analyzer._extract_required_years("3-5 years of relevant experience", {})
        assert years == 3.0

    def test_prefers_metadata(self, analyzer):
        years = analyzer._extract_required_years(
            "5+ years experience", {"required_years": 7}
        )
        assert years == 7.0

    def test_returns_zero_when_not_found(self, analyzer):
        years = analyzer._extract_required_years("Great job opportunity!", {})
        assert years == 0.0


# ---------------------------------------------------------------------------
# _detect_seniority
# ---------------------------------------------------------------------------


class TestDetectSeniority:
    def test_detects_senior(self, analyzer):
        level = analyzer._detect_seniority("senior engineer with extensive experience")
        assert level == "senior"

    def test_detects_entry(self, analyzer):
        level = analyzer._detect_seniority("entry level junior developer internship")
        assert level == "entry"

    def test_defaults_to_mid(self, analyzer):
        level = analyzer._detect_seniority("We need a good developer")
        assert level == "mid"

    def test_detects_management(self, analyzer):
        level = analyzer._detect_seniority("director of engineering, leadership role, head of")
        assert level == "management"


# ---------------------------------------------------------------------------
# _seniority_alignment
# ---------------------------------------------------------------------------


class TestSeniorityAlignment:
    def test_exact_match_returns_one(self, analyzer):
        assert analyzer._seniority_alignment("senior", "senior") == 1.0

    def test_one_level_off_returns_075(self, analyzer):
        assert analyzer._seniority_alignment("mid", "senior") == 0.75

    def test_two_levels_off_returns_04(self, analyzer):
        assert analyzer._seniority_alignment("entry", "senior") == 0.4

    def test_three_levels_off_returns_015(self, analyzer):
        assert analyzer._seniority_alignment("entry", "staff") == 0.15

    def test_unknown_level_returns_05(self, analyzer):
        assert analyzer._seniority_alignment("unknown", "senior") == 0.5


# ---------------------------------------------------------------------------
# _infer_candidate_seniority
# ---------------------------------------------------------------------------


class TestInferCandidateSeniority:
    def test_infers_from_title(self, analyzer):
        exp = [{"title": "Senior Developer"}]
        level = analyzer._infer_candidate_seniority(exp, 3)
        assert level == "senior"

    def test_infers_from_years_when_no_title_match(self, analyzer):
        exp = [{"title": "Developer"}]
        assert analyzer._infer_candidate_seniority(exp, 12) == "staff"
        assert analyzer._infer_candidate_seniority(exp, 6) == "senior"
        assert analyzer._infer_candidate_seniority(exp, 3) == "mid"
        assert analyzer._infer_candidate_seniority(exp, 1) == "entry"


# ---------------------------------------------------------------------------
# _match_responsibilities
# ---------------------------------------------------------------------------


class TestMatchResponsibilities:
    def test_no_requirements_returns_neutral(self, analyzer, sample_experience):
        score, details = analyzer._match_responsibilities(sample_experience, [])
        assert score == 0.5
        assert details == []

    def test_matches_found_in_experience(self, analyzer, sample_experience):
        score, details = analyzer._match_responsibilities(
            sample_experience, ["architect", "troubleshoot", "coordinate"]
        )
        assert score > 0.0
        assert len(details) == 2
        assert details[0]["title"] == "Senior Software Engineer"
