"""Unit tests for app.core.ats.optimizer.ATSOptimizer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.ats.optimizer import ATSOptimizer
from app.core.ats.scorer import ScoreDetails

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_skill_matcher() -> MagicMock:
    matcher = MagicMock()
    matcher.find_similar_skills.return_value = ["react", "vue"]
    return matcher


@pytest.fixture()
def optimizer(mock_skill_matcher: MagicMock) -> ATSOptimizer:
    return ATSOptimizer(skill_matcher=mock_skill_matcher)


def _make_score_details(**overrides) -> ScoreDetails:
    defaults = dict(
        overall_score=0.7,
        skill_score=0.8,
        experience_score=0.7,
        education_score=0.6,
        keyword_score=0.5,
        missing_required_skills=[],
        missing_preferred_skills=[],
        keyword_matches={},
        experience_matches=[],
        education_matches=[],
        improvement_suggestions=[],
    )
    defaults.update(overrides)
    return ScoreDetails(**defaults)


# ---------------------------------------------------------------------------
# suggest_improvements
# ---------------------------------------------------------------------------


class TestSuggestImprovements:
    def test_returns_list_of_strings(self, optimizer):
        sd = _make_score_details()
        result = optimizer.suggest_improvements(
            sd, "experienced python developer with experience education skills", "python developer"
        )
        assert isinstance(result, list)
        assert all(isinstance(s, str) for s in result)

    def test_missing_required_skills_produces_suggestion(self, optimizer):
        sd = _make_score_details(missing_required_skills=["python", "java"])
        result = optimizer.suggest_improvements(sd, "experience education skills", "python java developer")
        assert any("required skills" in s.lower() for s in result)

    def test_many_missing_skills_shows_count(self, optimizer):
        sd = _make_score_details(
            missing_required_skills=["python", "java", "go", "rust"]
        )
        result = optimizer.suggest_improvements(sd, "experience education skills", "developer")
        assert any("more" in s.lower() for s in result)

    def test_missing_preferred_skills_suggestion(self, optimizer):
        sd = _make_score_details(missing_preferred_skills=["react", "vue", "angular"])
        result = optimizer.suggest_improvements(sd, "experience education skills", "frontend")
        assert any("preferred" in s.lower() for s in result)

    def test_low_keyword_score_suggestion(self, optimizer):
        sd = _make_score_details(keyword_score=0.2)
        result = optimizer.suggest_improvements(
            sd, "experience education skills", "python developer"
        )
        assert any("keyword" in s.lower() for s in result)

    def test_low_experience_score_suggestion(self, optimizer):
        sd = _make_score_details(experience_score=0.3)
        result = optimizer.suggest_improvements(
            sd, "experience education skills", "developer"
        )
        assert any("experience" in s.lower() for s in result)

    def test_low_education_score_suggestion(self, optimizer):
        sd = _make_score_details(education_score=0.3)
        result = optimizer.suggest_improvements(
            sd, "experience education skills", "developer"
        )
        assert any("education" in s.lower() or "certification" in s.lower() for s in result)

    def test_carries_over_scorer_suggestions(self, optimizer):
        sd = _make_score_details(improvement_suggestions=["Custom suggestion from scorer"])
        result = optimizer.suggest_improvements(
            sd, "experience education skills", "developer"
        )
        assert "Custom suggestion from scorer" in result


# ---------------------------------------------------------------------------
# detect_industry
# ---------------------------------------------------------------------------


class TestDetectIndustry:
    def test_detects_software_engineering(self, optimizer):
        jd = "We need agile, ci/cd, docker, kubernetes, api, rest, microservices"
        assert optimizer.detect_industry(jd) == "software_engineering"

    def test_detects_data_science(self, optimizer):
        jd = "machine learning, deep learning, python, statistics, pandas, tensorflow"
        assert optimizer.detect_industry(jd) == "data_science"

    def test_returns_empty_for_low_confidence(self, optimizer):
        jd = "The weather is nice and sunny today."
        assert optimizer.detect_industry(jd) == ""


# ---------------------------------------------------------------------------
# get_missing_keywords
# ---------------------------------------------------------------------------


class TestGetMissingKeywords:
    def test_returns_missing_keywords_sorted_by_weight(self, optimizer):
        resume = "I know agile and scrum."
        missing = optimizer.get_missing_keywords(resume, "software_engineering")
        assert isinstance(missing, list)
        assert "agile" not in missing
        assert len(missing) > 0

    def test_returns_empty_for_unknown_industry(self, optimizer):
        assert optimizer.get_missing_keywords("text", "nonexistent_industry") == []


# ---------------------------------------------------------------------------
# _format_suggestions
# ---------------------------------------------------------------------------


class TestFormatSuggestions:
    def test_short_resume_gets_suggestion(self, optimizer):
        result = optimizer._format_suggestions("short resume text")
        assert any("short" in s.lower() for s in result)

    def test_missing_sections_gets_suggestion(self, optimizer):
        # Missing all standard sections
        result = optimizer._format_suggestions("some random text without sections")
        assert any("sections" in s.lower() for s in result)

    def test_complete_resume_no_format_issues(self, optimizer):
        text = " ".join(["word"] * 200) + " experience education skills"
        result = optimizer._format_suggestions(text)
        # Should not have the "short" warning
        assert not any("short" in s.lower() for s in result)
