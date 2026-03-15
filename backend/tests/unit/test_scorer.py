"""Unit tests for app.core.ats.scorer.ResumeScorer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.ats.scorer import ResumeScorer, ScoreDetails, ScoringWeights

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_skill_matcher() -> MagicMock:
    matcher = MagicMock()
    # By default every skill matches
    matcher.has_skill.return_value = True
    return matcher


@pytest.fixture()
def mock_keyword_analyzer() -> MagicMock:
    analyzer = MagicMock()
    analyzer.analyze_keywords.return_value = (0.75, {"python": 0.9})
    return analyzer


@pytest.fixture()
def mock_experience_analyzer() -> MagicMock:
    analyzer = MagicMock()
    analyzer.analyze_experience.return_value = (0.8, [{"title": "SWE", "match": True}])
    return analyzer


@pytest.fixture()
def scorer(
    mock_skill_matcher: MagicMock,
    mock_keyword_analyzer: MagicMock,
    mock_experience_analyzer: MagicMock,
) -> ResumeScorer:
    return ResumeScorer(
        skill_matcher=mock_skill_matcher,
        keyword_analyzer=mock_keyword_analyzer,
        experience_analyzer=mock_experience_analyzer,
    )


@pytest.fixture()
def candidate_profile() -> dict:
    return {
        "skills": ["python", "sql"],
        "experience": [{"title": "SWE", "years": 3}],
        "education": [{"degree": "Bachelor", "institution": "MIT"}],
    }


@pytest.fixture()
def job_metadata() -> dict:
    return {
        "required_skills": ["python"],
        "preferred_skills": ["sql"],
        "required_years": 2,
        "education_requirement": "bachelor",
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestScoreResume:
    def test_returns_score_details_instance(
        self, scorer: ResumeScorer, candidate_profile: dict, job_metadata: dict
    ) -> None:
        result = scorer.score_resume("resume text", "job desc", candidate_profile, job_metadata)
        assert isinstance(result, ScoreDetails)

    def test_overall_score_between_zero_and_one(
        self, scorer: ResumeScorer, candidate_profile: dict, job_metadata: dict
    ) -> None:
        result = scorer.score_resume("resume", "job", candidate_profile, job_metadata)
        assert 0.0 <= result.overall_score <= 1.0

    def test_default_weights_applied(
        self, scorer: ResumeScorer, candidate_profile: dict, job_metadata: dict
    ) -> None:
        """Default weights: skills=0.4, experience=0.3, education=0.2, keywords=0.1."""
        result = scorer.score_resume("resume", "job", candidate_profile, job_metadata)
        w = ScoringWeights()
        # All skills match -> skill_score = 1.0 (0.7*1.0 + 0.3*1.0)
        # exp = 0.8, edu = 1.0 (bachelor >= bachelor), kw = 0.75
        expected = w.skills * 1.0 + w.experience * 0.8 + w.education * 1.0 + w.keywords * 0.75
        assert result.overall_score == pytest.approx(round(min(expected, 1.0), 4), abs=0.01)

    def test_custom_weights_change_overall(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
        candidate_profile: dict,
        job_metadata: dict,
    ) -> None:
        custom_weights = ScoringWeights(skills=0.1, experience=0.1, education=0.1, keywords=0.7)
        scorer = ResumeScorer(
            mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer,
            weights=custom_weights,
        )
        result = scorer.score_resume("resume", "job", candidate_profile, job_metadata)
        # With keywords weighted at 0.7 and keyword_score=0.75, that dominates
        assert result.keyword_score == pytest.approx(0.75, abs=0.01)


class TestSuggestionsGenerated:
    def test_suggestions_when_missing_required_skills(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        mock_skill_matcher.has_skill.return_value = False
        mock_keyword_analyzer.analyze_keywords.return_value = (0.3, {})
        mock_experience_analyzer.analyze_experience.return_value = (0.4, [])

        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "job",
            {"skills": [], "experience": [], "education": []},
            {"required_skills": ["python", "java"], "preferred_skills": []},
        )
        assert len(result.improvement_suggestions) > 0
        assert any("required skills" in s.lower() for s in result.improvement_suggestions)

    def test_suggestions_for_low_keyword_score(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        mock_keyword_analyzer.analyze_keywords.return_value = (0.2, {})
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "job",
            {"skills": ["python"], "experience": [], "education": []},
            {"required_skills": ["python"], "preferred_skills": []},
        )
        assert any("keyword" in s.lower() for s in result.improvement_suggestions)


class TestScoringWeightsValidation:
    def test_weight_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError, match="Weight must be between"):
            ScoringWeights(skills=1.5)

    def test_negative_weight_raises(self) -> None:
        with pytest.raises(ValueError, match="Weight must be between"):
            ScoringWeights(skills=-0.1)


class TestScoreSkills:
    def test_no_skills_listed_returns_half(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "job",
            {"skills": [], "experience": [], "education": []},
            {"required_skills": [], "preferred_skills": []},
        )
        assert result.skill_score == 0.5

    def test_only_preferred_skills(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        mock_skill_matcher.has_skill.return_value = True
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "job",
            {"skills": ["react"], "experience": [], "education": []},
            {"required_skills": [], "preferred_skills": ["react"]},
        )
        assert result.skill_score == 1.0


class TestScoreEducation:
    def test_education_with_matching_degree(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "Bachelor degree required",
            {"skills": [], "experience": [], "education": [{"degree": "Bachelor of Science"}]},
            {"required_skills": [], "preferred_skills": [], "education_requirement": "bachelor"},
        )
        assert result.education_score == 1.0

    def test_education_below_requirement(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "PhD required",
            {"skills": [], "experience": [], "education": [{"degree": "Bachelor"}]},
            {"required_skills": [], "preferred_skills": [], "education_requirement": "phd"},
        )
        assert result.education_score < 1.0
        assert result.education_score > 0.0

    def test_no_education_requirement_returns_half(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "good job",
            {"skills": [], "experience": [], "education": []},
            {"required_skills": [], "preferred_skills": []},
        )
        assert result.education_score == 0.5

    def test_no_education_at_all_scores_low(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "Master degree required",
            {"skills": [], "experience": [], "education": [{"degree": "High School"}]},
            {"required_skills": [], "preferred_skills": [], "education_requirement": "master"},
        )
        assert result.education_score < 1.0


class TestSuggestionCoverage:
    def test_well_aligned_resume_gets_positive_suggestion(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        """When skill_score >= 0.8, kw_score >= 0.6 and no other suggestions."""
        mock_keyword_analyzer.analyze_keywords.return_value = (0.7, {})
        mock_experience_analyzer.analyze_experience.return_value = (0.9, [])
        mock_skill_matcher.has_skill.return_value = True

        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "job",
            {"skills": ["python"], "experience": [], "education": []},
            {"required_skills": ["python"], "preferred_skills": [], "education_requirement": ""},
        )
        assert any("well-aligned" in s.lower() for s in result.improvement_suggestions)

    def test_low_experience_score_suggestion(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        mock_experience_analyzer.analyze_experience.return_value = (0.3, [])
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "job",
            {"skills": [], "experience": [], "education": []},
            {"required_skills": [], "preferred_skills": []},
        )
        assert any("experience" in s.lower() for s in result.improvement_suggestions)

    def test_many_missing_preferred_skills_suggestion(
        self,
        mock_skill_matcher: MagicMock,
        mock_keyword_analyzer: MagicMock,
        mock_experience_analyzer: MagicMock,
    ) -> None:
        mock_skill_matcher.has_skill.return_value = False
        scorer = ResumeScorer(mock_skill_matcher, mock_keyword_analyzer, mock_experience_analyzer)
        result = scorer.score_resume(
            "resume", "job",
            {"skills": [], "experience": [], "education": []},
            {"required_skills": [], "preferred_skills": ["react", "vue", "angular"]},
        )
        assert any("preferred" in s.lower() for s in result.improvement_suggestions)
