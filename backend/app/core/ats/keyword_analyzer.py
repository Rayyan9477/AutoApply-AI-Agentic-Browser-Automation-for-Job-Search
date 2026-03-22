"""Keyword analysis engine for resume-to-job-description matching.

Combines TF-IDF scoring, semantic similarity, and phrase matching to
produce a keyword overlap score between a resume and a job description.
"""

from __future__ import annotations

import math
from collections import Counter

import spacy
import structlog

logger = structlog.get_logger(__name__)

# Domain-specific terms that carry extra weight when matched.
INDUSTRY_TERMS: dict[str, list[str]] = {
    "software_engineering": [
        "algorithms", "data structures", "system design", "microservices",
        "api", "rest", "graphql", "testing", "code review", "version control",
        "debugging", "performance optimization", "scalability", "architecture",
    ],
    "data_science": [
        "statistical analysis", "feature engineering", "model training",
        "data pipeline", "etl", "visualization", "hypothesis testing",
        "a/b testing", "regression", "classification", "clustering",
    ],
    "devops": [
        "infrastructure as code", "monitoring", "alerting", "deployment",
        "containerization", "orchestration", "load balancing", "high availability",
        "disaster recovery", "configuration management", "observability",
    ],
    "product_management": [
        "roadmap", "stakeholder", "user stories", "sprint planning",
        "backlog", "metrics", "kpi", "okr", "prioritization",
        "market research", "competitive analysis", "go-to-market",
    ],
    "cybersecurity": [
        "vulnerability assessment", "penetration testing", "encryption",
        "firewall", "intrusion detection", "compliance", "soc",
        "incident response", "threat modeling", "zero trust",
    ],
}

# Common stop words to exclude from keyword extraction.
_STOP_WORDS: set[str] = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "must", "and", "or",
    "but", "if", "than", "that", "this", "these", "those", "with", "for",
    "from", "into", "to", "in", "on", "at", "by", "of", "about", "as",
    "not", "no", "we", "you", "they", "our", "your", "their", "its",
    "it", "he", "she", "who", "which", "what", "when", "where", "how",
}


class KeywordAnalyzer:
    """Analyzes keyword overlap between resumes and job descriptions.

    Uses TF-IDF weighting, spaCy semantic similarity, and multi-word
    phrase detection to compute a composite keyword match score.

    Args:
        nlp: A loaded spaCy language model with word vectors.
    """

    def __init__(self, nlp: spacy.Language) -> None:
        self._nlp = nlp
        logger.info("keyword_analyzer.initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_keywords(
        self,
        resume_text: str,
        job_description: str,
    ) -> tuple[float, dict[str, float]]:
        """Compute a keyword match score between resume and job description.

        The score is a weighted combination of:
        - TF-IDF overlap (40%)
        - Semantic similarity (30%)
        - Phrase match ratio (30%)

        Args:
            resume_text: Full text of the candidate resume.
            job_description: Full text of the job posting.

        Returns:
            A tuple of (overall_score, per_keyword_scores) where the score
            is in [0, 1] and per_keyword_scores maps each job keyword to
            its individual match strength.
        """
        if not resume_text.strip() or not job_description.strip():
            logger.warning("keyword_analyzer.empty_input")
            return 0.0, {}

        job_keywords = self._extract_keywords(job_description)
        resume_keywords = self._extract_keywords(resume_text)

        if not job_keywords:
            return 0.0, {}

        tfidf_score, per_keyword = self._tfidf_overlap(
            resume_keywords, job_keywords, resume_text,
        )
        semantic_score = self._semantic_similarity(resume_text, job_description)
        phrase_score = self._phrase_match_score(resume_text, job_description)

        overall = (0.4 * tfidf_score) + (0.3 * semantic_score) + (0.3 * phrase_score)
        overall = min(max(overall, 0.0), 1.0)

        logger.debug(
            "keyword_analyzer.scores",
            tfidf=round(tfidf_score, 3),
            semantic=round(semantic_score, 3),
            phrase=round(phrase_score, 3),
            overall=round(overall, 3),
        )
        return overall, per_keyword

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract meaningful keywords from text using spaCy NLP."""
        doc = self._nlp(text.lower())
        keywords: list[str] = []
        for token in doc:
            if (
                not token.is_stop
                and not token.is_punct
                and not token.is_space
                and token.text not in _STOP_WORDS
                and len(token.text) > 2
            ):
                keywords.append(token.lemma_)

        # Also extract noun chunks as multi-word phrases.
        for chunk in doc.noun_chunks:
            phrase = chunk.text.strip()
            if len(phrase.split()) >= 2 and phrase not in _STOP_WORDS:
                keywords.append(phrase)

        return keywords

    def _tfidf_overlap(
        self,
        resume_keywords: list[str],
        job_keywords: list[str],
        resume_text: str,
    ) -> tuple[float, dict[str, float]]:
        """Calculate TF-IDF-weighted overlap between keyword sets."""
        job_freq = Counter(job_keywords)
        resume_lower = resume_text.lower()
        total_job_kw = len(job_freq)
        if total_job_kw == 0:
            return 0.0, {}

        per_keyword: dict[str, float] = {}
        matched_weight = 0.0
        total_weight = 0.0

        for keyword, count in job_freq.items():
            weight = 1.0 + math.log(1 + count)
            total_weight += weight
            if keyword in resume_lower:
                per_keyword[keyword] = min(weight / (1.0 + math.log(1 + total_job_kw)), 1.0)
                matched_weight += weight
            else:
                per_keyword[keyword] = 0.0

        score = matched_weight / total_weight if total_weight > 0 else 0.0
        return min(score, 1.0), per_keyword

    def _semantic_similarity(self, resume_text: str, job_description: str) -> float:
        """Calculate spaCy document-level semantic similarity."""
        resume_doc = self._nlp(resume_text[:10_000])  # cap length for performance
        job_doc = self._nlp(job_description[:10_000])
        if not resume_doc.has_vector or not job_doc.has_vector:
            return 0.0
        sim = float(resume_doc.similarity(job_doc))
        return max(sim, 0.0)

    def _phrase_match_score(self, resume_text: str, job_description: str) -> float:
        """Score based on multi-word phrase matches from the job description."""
        job_doc = self._nlp(job_description.lower())
        phrases: list[str] = []
        for chunk in job_doc.noun_chunks:
            phrase = chunk.text.strip()
            if len(phrase.split()) >= 2:
                phrases.append(phrase)

        # Also check industry term phrases.
        for terms in INDUSTRY_TERMS.values():
            for term in terms:
                if term in job_description.lower():
                    phrases.append(term)

        if not phrases:
            return 0.0

        unique_phrases = list(set(phrases))
        resume_lower = resume_text.lower()
        matches = sum(1 for p in unique_phrases if p in resume_lower)
        return matches / len(unique_phrases)

    def detect_domain(self, text: str) -> str | None:
        """Detect the industry domain of a text based on term frequency.

        Args:
            text: Job description or resume text.

        Returns:
            The best-matching domain key, or None if no match.
        """
        lower = text.lower()
        best_domain: str | None = None
        best_count = 0
        for domain, terms in INDUSTRY_TERMS.items():
            count = sum(1 for t in terms if t in lower)
            if count > best_count:
                best_count = count
                best_domain = domain
        return best_domain if best_count >= 2 else None
