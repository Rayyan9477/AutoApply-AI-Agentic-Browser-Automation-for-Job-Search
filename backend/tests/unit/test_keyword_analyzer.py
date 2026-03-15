"""Unit tests for app.core.ats.keyword_analyzer.KeywordAnalyzer."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.core.ats.keyword_analyzer import KeywordAnalyzer

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_nlp() -> MagicMock:
    """Create a spaCy nlp mock with token and noun_chunk support."""
    nlp = MagicMock()

    def _make_token(text):
        t = MagicMock()
        t.text = text
        t.lemma_ = text
        t.is_stop = False
        t.is_punct = text in {".", ",", ";", ":", "!", "?"}
        t.is_space = text.strip() == ""
        return t

    def _nlp_call(text):
        doc = MagicMock()
        words = text.split()
        doc.__iter__ = lambda self: iter([_make_token(w) for w in words])
        # Return empty noun_chunks by default
        doc.noun_chunks = []
        doc.has_vector = True
        doc.similarity = MagicMock(return_value=0.7)
        return doc

    nlp.side_effect = _nlp_call
    return nlp


@pytest.fixture()
def analyzer(mock_nlp: MagicMock) -> KeywordAnalyzer:
    return KeywordAnalyzer(nlp=mock_nlp)


# ---------------------------------------------------------------------------
# analyze_keywords
# ---------------------------------------------------------------------------


class TestAnalyzeKeywords:
    def test_returns_tuple_of_score_and_dict(self, analyzer):
        score, per_kw = analyzer.analyze_keywords(
            "python developer experience", "python developer needed"
        )
        assert isinstance(score, float)
        assert isinstance(per_kw, dict)

    def test_score_between_zero_and_one(self, analyzer):
        score, _ = analyzer.analyze_keywords(
            "python developer with docker experience",
            "looking for python developer with docker skills",
        )
        assert 0.0 <= score <= 1.0

    def test_empty_resume_returns_zero(self, analyzer):
        score, per_kw = analyzer.analyze_keywords("", "python developer")
        assert score == 0.0
        assert per_kw == {}

    def test_empty_job_description_returns_zero(self, analyzer):
        score, per_kw = analyzer.analyze_keywords("python developer", "")
        assert score == 0.0
        assert per_kw == {}

    def test_whitespace_only_returns_zero(self, analyzer):
        score, _per_kw = analyzer.analyze_keywords("   ", "   ")
        assert score == 0.0


# ---------------------------------------------------------------------------
# TF-IDF overlap
# ---------------------------------------------------------------------------


class TestTfidfOverlap:
    def test_perfect_overlap_scores_high(self, analyzer):
        score, _per_kw = analyzer._tfidf_overlap(
            ["python", "docker"], ["python", "docker"], "python docker"
        )
        assert score > 0.5

    def test_no_overlap_scores_zero(self, analyzer):
        score, per_kw = analyzer._tfidf_overlap(
            ["java", "spring"], ["python", "docker"], "java spring"
        )
        assert score == 0.0
        assert per_kw["python"] == 0.0
        assert per_kw["docker"] == 0.0

    def test_empty_job_keywords_returns_zero(self, analyzer):
        score, per_kw = analyzer._tfidf_overlap(
            ["python"], [], "python"
        )
        assert score == 0.0
        assert per_kw == {}


# ---------------------------------------------------------------------------
# Semantic similarity
# ---------------------------------------------------------------------------


class TestSemanticSimilarity:
    def test_returns_float(self, analyzer):
        score = analyzer._semantic_similarity("python dev", "python developer")
        assert isinstance(score, float)

    def test_no_vector_returns_zero(self, mock_nlp):
        def _no_vec(text):
            doc = MagicMock()
            doc.has_vector = False
            return doc

        mock_nlp.side_effect = _no_vec
        analyzer = KeywordAnalyzer(nlp=mock_nlp)
        score = analyzer._semantic_similarity("test", "test")
        assert score == 0.0


# ---------------------------------------------------------------------------
# Phrase matching
# ---------------------------------------------------------------------------


class TestPhraseMatchScore:
    def test_no_phrases_returns_zero(self, analyzer):
        score = analyzer._phrase_match_score("python", "python")
        assert score == 0.0

    def test_industry_term_phrase_match(self, mock_nlp):
        """If job description contains an industry term, and resume does too."""
        def _nlp_with_chunks(text):
            doc = MagicMock()
            doc.__iter__ = lambda self: iter([])
            doc.noun_chunks = []
            doc.has_vector = True
            doc.similarity = MagicMock(return_value=0.7)
            return doc

        mock_nlp.side_effect = _nlp_with_chunks
        analyzer = KeywordAnalyzer(nlp=mock_nlp)
        # "system design" is in software_engineering INDUSTRY_TERMS
        score = analyzer._phrase_match_score(
            "experienced in system design and architecture",
            "requires system design and architecture skills"
        )
        assert score > 0.0


# ---------------------------------------------------------------------------
# detect_domain
# ---------------------------------------------------------------------------


class TestDetectDomain:
    def test_detects_software_engineering(self, analyzer):
        text = (
            "We need someone with microservices experience, "
            "api design, system design, and code review skills."
        )
        domain = analyzer.detect_domain(text)
        assert domain == "software_engineering"

    def test_returns_none_for_generic_text(self, analyzer):
        domain = analyzer.detect_domain("The weather is nice today.")
        assert domain is None

    def test_requires_at_least_two_matches(self, analyzer):
        # Only one match should return None
        domain = analyzer.detect_domain("We need monitoring skills.")
        assert domain is None

    def test_detects_data_science(self, analyzer):
        text = (
            "statistical analysis, feature engineering, "
            "model training, data pipeline"
        )
        domain = analyzer.detect_domain(text)
        assert domain == "data_science"
