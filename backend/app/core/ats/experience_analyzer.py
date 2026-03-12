"""Experience analysis engine for resume scoring.

Evaluates candidate work experience against job requirements by
extracting required years, matching responsibilities, and assessing
seniority alignment.
"""

from __future__ import annotations

import re
from typing import Any

import spacy
import structlog

logger = structlog.get_logger(__name__)

# Terms that indicate experience level in job descriptions.
SENIORITY_TERMS: dict[str, list[str]] = {
    "entry": [
        "entry level", "junior", "associate", "intern", "internship",
        "graduate", "new grad", "early career", "0-2 years",
    ],
    "mid": [
        "mid level", "mid-level", "intermediate", "3-5 years",
        "2-5 years", "3+ years", "several years",
    ],
    "senior": [
        "senior", "sr.", "lead", "principal", "5+ years",
        "7+ years", "extensive experience", "seasoned",
    ],
    "staff": [
        "staff", "staff engineer", "distinguished", "10+ years",
        "expert level", "deep expertise",
    ],
    "management": [
        "manager", "director", "vp", "vice president", "head of",
        "chief", "c-level", "executive", "leadership role",
    ],
}

# Responsibility categories used for matching.
RESPONSIBILITY_CATEGORIES: dict[str, list[str]] = {
    "technical_leadership": [
        "architect", "design system", "technical direction",
        "code review", "mentoring", "technical strategy",
    ],
    "project_delivery": [
        "deliver", "ship", "launch", "deploy", "release",
        "project management", "sprint", "milestone",
    ],
    "collaboration": [
        "cross-functional", "stakeholder", "collaborate",
        "team", "coordinate", "partner with",
    ],
    "problem_solving": [
        "troubleshoot", "debug", "optimize", "improve",
        "resolve", "investigate", "root cause",
    ],
    "communication": [
        "present", "document", "report", "communicate",
        "write", "proposal", "specification",
    ],
}


class ExperienceAnalyzer:
    """Evaluates candidate experience against job requirements.

    Extracts required years of experience from job descriptions,
    matches candidate responsibilities to job expectations, and
    assesses seniority-level alignment.

    Args:
        nlp: A loaded spaCy language model, or None to disable
             semantic matching (falls back to keyword matching).
    """

    def __init__(self, nlp: spacy.Language | None = None) -> None:
        self._nlp = nlp
        logger.info("experience_analyzer.initialized", has_nlp=nlp is not None)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze_experience(
        self,
        candidate_experience: list[dict[str, Any]],
        job_description: str,
        job_metadata: dict[str, Any],
    ) -> tuple[float, list[dict[str, Any]]]:
        """Analyze how well candidate experience matches the job.

        Args:
            candidate_experience: List of experience entries, each with
                keys like ``title``, ``company``, ``duration_years``,
                ``description``, ``responsibilities``.
            job_description: Full text of the job posting.
            job_metadata: Structured job data (may contain
                ``required_years``, ``seniority_level``, etc.).

        Returns:
            A tuple of (score, details) where score is in [0, 1] and
            details is a list of per-entry match breakdowns.
        """
        if not candidate_experience:
            logger.warning("experience_analyzer.no_candidate_experience")
            return 0.0, []

        required_years = self._extract_required_years(
            job_description, job_metadata,
        )
        job_seniority = self._detect_seniority(job_description)
        key_responsibilities = self._extract_key_responsibilities(job_description)

        total_years = sum(
            entry.get("duration_years", 0) for entry in candidate_experience
        )

        # --- Years-of-experience score (0-1) ---
        if required_years > 0:
            years_ratio = total_years / required_years
            years_score = min(years_ratio, 1.0)
        else:
            years_score = min(total_years / 3.0, 1.0)  # default baseline

        # --- Seniority alignment score ---
        candidate_seniority = self._infer_candidate_seniority(
            candidate_experience, total_years,
        )
        seniority_score = self._seniority_alignment(
            candidate_seniority, job_seniority,
        )

        # --- Responsibility match score ---
        resp_score, entry_details = self._match_responsibilities(
            candidate_experience, key_responsibilities,
        )

        # Weighted combination
        overall = (0.35 * years_score) + (0.30 * resp_score) + (0.35 * seniority_score)
        overall = min(max(overall, 0.0), 1.0)

        logger.debug(
            "experience_analyzer.scores",
            years_score=round(years_score, 3),
            seniority_score=round(seniority_score, 3),
            responsibility_score=round(resp_score, 3),
            overall=round(overall, 3),
        )
        return overall, entry_details

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_required_years(
        self,
        job_description: str,
        job_metadata: dict[str, Any],
    ) -> float:
        """Extract required years of experience from job text or metadata."""
        if "required_years" in job_metadata:
            return float(job_metadata["required_years"])

        patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of)?\s*(?:experience|exp)",
            r"(?:minimum|at least|min)\s*(\d+)\s*(?:years?|yrs?)",
            r"(\d+)\s*-\s*\d+\s*(?:years?|yrs?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, job_description, re.IGNORECASE)
            if match:
                return float(match.group(1))
        return 0.0

    def _extract_key_responsibilities(self, job_description: str) -> list[str]:
        """Extract key responsibility phrases from the job description."""
        responsibilities: list[str] = []
        lower = job_description.lower()
        for category_terms in RESPONSIBILITY_CATEGORIES.values():
            for term in category_terms:
                if term in lower:
                    responsibilities.append(term)
        return responsibilities

    def _detect_seniority(self, job_description: str) -> str:
        """Detect the seniority level implied by the job description."""
        lower = job_description.lower()
        best_level = "mid"  # default
        best_count = 0
        for level, terms in SENIORITY_TERMS.items():
            count = sum(1 for t in terms if t in lower)
            if count > best_count:
                best_count = count
                best_level = level
        return best_level

    def _infer_candidate_seniority(
        self,
        experience: list[dict[str, Any]],
        total_years: float,
    ) -> str:
        """Infer candidate seniority from their experience history."""
        titles = " ".join(
            entry.get("title", "").lower() for entry in experience
        )
        for level, terms in SENIORITY_TERMS.items():
            for term in terms:
                if term in titles:
                    return level

        if total_years >= 10:
            return "staff"
        if total_years >= 5:
            return "senior"
        if total_years >= 2:
            return "mid"
        return "entry"

    def _seniority_alignment(self, candidate: str, required: str) -> float:
        """Score how well candidate seniority aligns with the requirement."""
        levels = ["entry", "mid", "senior", "staff", "management"]
        try:
            c_idx = levels.index(candidate)
            r_idx = levels.index(required)
        except ValueError:
            return 0.5

        diff = abs(c_idx - r_idx)
        if diff == 0:
            return 1.0
        if diff == 1:
            return 0.75
        if diff == 2:
            return 0.4
        return 0.15

    def _match_responsibilities(
        self,
        candidate_experience: list[dict[str, Any]],
        key_responsibilities: list[str],
    ) -> tuple[float, list[dict[str, Any]]]:
        """Match candidate responsibilities against job requirements."""
        if not key_responsibilities:
            return 0.5, []  # neutral when no explicit requirements

        details: list[dict[str, Any]] = []
        all_matched: set[str] = set()

        for entry in candidate_experience:
            entry_text = " ".join([
                entry.get("description", ""),
                " ".join(entry.get("responsibilities", [])),
                entry.get("title", ""),
            ]).lower()

            matched = [r for r in key_responsibilities if r in entry_text]
            all_matched.update(matched)
            details.append({
                "title": entry.get("title", "Unknown"),
                "company": entry.get("company", "Unknown"),
                "matched_responsibilities": matched,
                "match_count": len(matched),
            })

        score = len(all_matched) / len(key_responsibilities)
        return min(score, 1.0), details
