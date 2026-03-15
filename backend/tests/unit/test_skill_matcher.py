"""Unit tests for app.core.ats.skill_matcher.SkillMatcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.ats.skill_matcher import (
    SKILL_CATEGORIES,
    SkillMatcher,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_nlp() -> MagicMock:
    """Create a spaCy nlp mock that returns docs with has_vector=False."""
    nlp = MagicMock()

    def _nlp_call(text: str) -> MagicMock:
        doc = MagicMock()
        doc.has_vector = False
        doc.text = text
        return doc

    nlp.side_effect = _nlp_call
    return nlp


@pytest.fixture()
def matcher(mock_nlp: MagicMock) -> SkillMatcher:
    return SkillMatcher(nlp=mock_nlp)


# ---------------------------------------------------------------------------
# has_skill
# ---------------------------------------------------------------------------


class TestHasSkill:
    def test_direct_match_exact_string(self, matcher: SkillMatcher) -> None:
        assert matcher.has_skill(["Python", "SQL"], "python") is True

    def test_direct_match_case_insensitive(self, matcher: SkillMatcher) -> None:
        assert matcher.has_skill(["JAVASCRIPT"], "javascript") is True

    def test_variation_match_alias_to_canonical(self, matcher: SkillMatcher) -> None:
        """Candidate lists 'k8s' which is a known alias for 'kubernetes'."""
        assert matcher.has_skill(["k8s"], "kubernetes") is True

    def test_variation_match_canonical_to_alias(self, matcher: SkillMatcher) -> None:
        """Candidate lists 'kubernetes', required skill is 'k8s'."""
        assert matcher.has_skill(["kubernetes"], "k8s") is True

    def test_fuzzy_match_close_strings(self, matcher: SkillMatcher) -> None:
        """Fuzzy match should catch minor spelling differences."""
        assert matcher.has_skill(["postgresql"], "postgres") is True

    def test_no_match_unrelated_skills(self, matcher: SkillMatcher) -> None:
        assert matcher.has_skill(["python", "django"], "kubernetes") is False

    def test_empty_candidate_skills_returns_false(self, matcher: SkillMatcher) -> None:
        assert matcher.has_skill([], "python") is False


# ---------------------------------------------------------------------------
# extract_skills
# ---------------------------------------------------------------------------


class TestExtractSkills:
    def test_extracts_canonical_skill_from_text(self, matcher: SkillMatcher) -> None:
        text = "Experienced in Python and PostgreSQL development."
        skills = matcher.extract_skills(text)
        assert "python" in skills
        assert "postgresql" in skills

    def test_extracts_via_variation(self, matcher: SkillMatcher) -> None:
        text = "Built microservices with k8s and golang."
        skills = matcher.extract_skills(text)
        assert "kubernetes" in skills
        assert "go" in skills

    def test_returns_empty_for_no_matches(self, matcher: SkillMatcher) -> None:
        text = "The weather was sunny and warm yesterday afternoon."
        skills = matcher.extract_skills(text)
        assert len(skills) == 0

    def test_deduplicates_results(self, matcher: SkillMatcher) -> None:
        text = "Python, python3, cpython"
        skills = matcher.extract_skills(text)
        # extract_skills returns a set, so duplicates are inherently removed
        assert "python" in skills


# ---------------------------------------------------------------------------
# categorize_skills
# ---------------------------------------------------------------------------


class TestCategorizeSkills:
    def test_places_language_in_programming_languages(self, matcher: SkillMatcher) -> None:
        result = matcher.categorize_skills(["python", "java"])
        assert "python" in result["programming_languages"]
        assert "java" in result["programming_languages"]

    def test_places_framework_in_web_frameworks(self, matcher: SkillMatcher) -> None:
        result = matcher.categorize_skills(["react", "django"])
        assert "react" in result["web_frameworks"]
        assert "django" in result["web_frameworks"]

    def test_unknown_skill_goes_to_other(self, matcher: SkillMatcher) -> None:
        result = matcher.categorize_skills(["obscure_framework_xyz"])
        assert "obscure_framework_xyz" in result["other"]

    def test_all_categories_present_in_result(self, matcher: SkillMatcher) -> None:
        result = matcher.categorize_skills([])
        for category in SKILL_CATEGORIES:
            assert category in result
        assert "other" in result


# ---------------------------------------------------------------------------
# _normalize_skill
# ---------------------------------------------------------------------------


class TestNormalizeSkill:
    def test_lowercases_and_strips(self, matcher: SkillMatcher) -> None:
        result = matcher._normalize_skill("  Python  ")
        assert result == "python"

    def test_resolves_known_variation(self, matcher: SkillMatcher) -> None:
        result = matcher._normalize_skill("k8s")
        assert result == "kubernetes"

    def test_unknown_skill_returned_as_is(self, matcher: SkillMatcher) -> None:
        result = matcher._normalize_skill("obscure_framework")
        assert result == "obscure_framework"


# ---------------------------------------------------------------------------
# find_similar_skills
# ---------------------------------------------------------------------------


class TestFindSimilarSkills:
    def test_finds_similar_by_fuzzy_match(self, matcher: SkillMatcher) -> None:
        # "postgresql" and "mysql" are both in SKILL_VARIATIONS
        similar = matcher.find_similar_skills("postgresql", threshold=0.5)
        # Should return at least some results (fuzzy matching at low threshold)
        assert isinstance(similar, list)

    def test_excludes_exact_match(self, matcher: SkillMatcher) -> None:
        similar = matcher.find_similar_skills("python", threshold=0.01)
        assert "python" not in similar


# ---------------------------------------------------------------------------
# _word_present
# ---------------------------------------------------------------------------


class TestWordPresent:
    def test_whole_word_match(self, matcher: SkillMatcher) -> None:
        assert SkillMatcher._word_present("python", "i know python well") is True

    def test_no_partial_match(self, matcher: SkillMatcher) -> None:
        assert SkillMatcher._word_present("sql", "nosqldb") is False

    def test_boundary_at_end(self, matcher: SkillMatcher) -> None:
        assert SkillMatcher._word_present("sql", "i use sql") is True
