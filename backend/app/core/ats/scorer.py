"""Resume scoring engine with multi-factor weighted analysis.

Orchestrates skill matching, keyword analysis, experience evaluation,
and education verification to produce a composite ATS compatibility score.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.ats.experience_analyzer import ExperienceAnalyzer
from app.core.ats.keyword_analyzer import KeywordAnalyzer
from app.core.ats.skill_matcher import SkillMatcher

logger = structlog.get_logger(__name__)

_EDUCATION_LEVELS: dict[str, int] = {
    "high school": 1, "associate": 2, "bachelor": 3,
    "master": 4, "phd": 5, "doctorate": 5,
}

_EDUCATION_PATTERNS: list[str] = [
    r"(?:bachelor|bs|ba|b\.s\.|b\.a\.)\s*(?:degree|'s)?",
    r"(?:master|ms|ma|m\.s\.|m\.a\.)\s*(?:degree|'s)?",
    r"(?:phd|ph\.d\.|doctorate)\s*(?:degree)?",
    r"(?:associate|as|a\.s\.)\s*(?:degree|'s)?",
    r"(?:high school|ged|diploma)",
]


class ScoringWeights(BaseModel):
    """Configurable weights for each scoring factor.

    All weights must be between 0 and 1 and should sum to 1.0.
    """

    model_config = ConfigDict(frozen=True)
    skills: float = 0.4
    experience: float = 0.3
    education: float = 0.2
    keywords: float = 0.1

    @field_validator("skills", "experience", "education", "keywords")
    @classmethod
    def _weight_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0 and 1, got {v}")
        return v


class ScoreDetails(BaseModel):
    """Detailed breakdown of a resume scoring result."""

    model_config = ConfigDict(frozen=True)
    overall_score: float
    skill_score: float
    experience_score: float
    education_score: float
    keyword_score: float
    missing_required_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    keyword_matches: dict[str, float] = Field(default_factory=dict)
    experience_matches: list[dict[str, Any]] = Field(default_factory=list)
    education_matches: list[dict[str, Any]] = Field(default_factory=list)
    improvement_suggestions: list[str] = Field(default_factory=list)


class ResumeScorer:
    """Scores resumes against job descriptions using multi-factor analysis.

    Args:
        skill_matcher: Injected SkillMatcher instance.
        keyword_analyzer: Injected KeywordAnalyzer instance.
        experience_analyzer: Injected ExperienceAnalyzer instance.
        weights: Optional custom scoring weights.
    """

    def __init__(
        self,
        skill_matcher: SkillMatcher,
        keyword_analyzer: KeywordAnalyzer,
        experience_analyzer: ExperienceAnalyzer,
        weights: ScoringWeights | None = None,
    ) -> None:
        self._skill_matcher = skill_matcher
        self._keyword_analyzer = keyword_analyzer
        self._experience_analyzer = experience_analyzer
        self._weights = weights or ScoringWeights()
        logger.info("resume_scorer.initialized", weights=self._weights.model_dump())

    def score_resume(
        self,
        resume_text: str,
        job_description: str,
        candidate_profile: dict[str, Any],
        job_metadata: dict[str, Any],
    ) -> ScoreDetails:
        """Score a resume against a job description.

        Args:
            resume_text: Full text content of the resume.
            job_description: Full text of the job posting.
            candidate_profile: Structured candidate data with keys
                ``skills``, ``experience``, ``education``.
            job_metadata: Structured job data with keys like
                ``required_skills``, ``preferred_skills``,
                ``required_years``, ``education_requirement``.

        Returns:
            A ScoreDetails instance with the full scoring breakdown.
        """
        skill_score, missing_req, missing_pref = self._score_skills(
            candidate_profile.get("skills", []),
            job_metadata.get("required_skills", []),
            job_metadata.get("preferred_skills", []),
        )
        keyword_score, keyword_matches = self._keyword_analyzer.analyze_keywords(
            resume_text, job_description,
        )
        exp_score, exp_matches = self._experience_analyzer.analyze_experience(
            candidate_profile.get("experience", []),
            job_description, job_metadata,
        )
        edu_score, edu_matches = self._score_education(
            candidate_profile.get("education", []),
            job_description, job_metadata,
        )

        w = self._weights
        overall = (
            w.skills * skill_score + w.experience * exp_score
            + w.education * edu_score + w.keywords * keyword_score
        )
        overall = min(max(overall, 0.0), 1.0)

        suggestions = self._generate_suggestions(
            skill_score, exp_score, edu_score, keyword_score,
            missing_req, missing_pref,
        )

        details = ScoreDetails(
            overall_score=round(overall, 4),
            skill_score=round(skill_score, 4),
            experience_score=round(exp_score, 4),
            education_score=round(edu_score, 4),
            keyword_score=round(keyword_score, 4),
            missing_required_skills=missing_req,
            missing_preferred_skills=missing_pref,
            keyword_matches=keyword_matches,
            experience_matches=exp_matches,
            education_matches=edu_matches,
            improvement_suggestions=suggestions,
        )
        logger.info(
            "resume_scorer.scored", overall=details.overall_score,
            skills=details.skill_score, experience=details.experience_score,
            education=details.education_score, keywords=details.keyword_score,
        )
        return details

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _score_skills(
        self,
        candidate_skills: list[str],
        required_skills: list[str],
        preferred_skills: list[str],
    ) -> tuple[float, list[str], list[str]]:
        """Score skill coverage and identify gaps."""
        if not required_skills and not preferred_skills:
            return 0.5, [], []

        missing_required = [
            s for s in required_skills
            if not self._skill_matcher.has_skill(candidate_skills, s)
        ]
        missing_preferred = [
            s for s in preferred_skills
            if not self._skill_matcher.has_skill(candidate_skills, s)
        ]
        req_matched = len(required_skills) - len(missing_required)
        pref_matched = len(preferred_skills) - len(missing_preferred)
        req_ratio = req_matched / (len(required_skills) or 1)
        pref_ratio = pref_matched / (len(preferred_skills) or 1)

        if required_skills and preferred_skills:
            score = 0.7 * req_ratio + 0.3 * pref_ratio
        elif required_skills:
            score = req_ratio
        else:
            score = pref_ratio
        return min(score, 1.0), missing_required, missing_preferred

    def _score_education(
        self,
        candidate_education: list[dict[str, Any]],
        job_description: str,
        job_metadata: dict[str, Any],
    ) -> tuple[float, list[dict[str, Any]]]:
        """Score education alignment with job requirements."""
        required_level = job_metadata.get("education_requirement", "")
        if not required_level:
            required_level = self._extract_education_requirement(job_description)
        if not required_level:
            return 0.5, []

        required_rank = self._education_rank(required_level)
        matches: list[dict[str, Any]] = []
        best_rank = 0
        for edu in candidate_education:
            degree = edu.get("degree", "")
            rank = self._education_rank(degree)
            matches.append({
                "degree": degree,
                "institution": edu.get("institution", "Unknown"),
                "rank": rank,
                "meets_requirement": rank >= required_rank,
            })
            best_rank = max(best_rank, rank)

        if best_rank >= required_rank:
            score = 1.0
        elif best_rank > 0:
            score = best_rank / required_rank
        else:
            score = 0.2
        return score, matches

    def _extract_education_requirement(self, job_description: str) -> str:
        """Extract education requirement from job description text."""
        lower = job_description.lower()
        for pattern in _EDUCATION_PATTERNS:
            match = re.search(pattern, lower)
            if match:
                return match.group(0).strip()
        return ""

    def _education_rank(self, education_text: str) -> int:
        """Convert an education string to a numeric rank."""
        lower = education_text.lower()
        for level, rank in _EDUCATION_LEVELS.items():
            if level in lower:
                return rank
        return 0

    def _generate_suggestions(
        self, skill_score: float, exp_score: float,
        edu_score: float, kw_score: float,
        missing_req: list[str], missing_pref: list[str],
    ) -> list[str]:
        """Generate actionable improvement suggestions."""
        suggestions: list[str] = []
        if missing_req:
            suggestions.append(
                f"Add required skills to your resume: {', '.join(missing_req[:5])}"
            )
        if len(missing_pref) > 2:
            suggestions.append(
                f"Consider highlighting preferred skills: {', '.join(missing_pref[:3])}"
            )
        if kw_score < 0.4:
            suggestions.append(
                "Increase keyword alignment by mirroring terminology from the job description."
            )
        if exp_score < 0.5:
            suggestions.append(
                "Strengthen experience descriptions by quantifying achievements "
                "and aligning responsibilities with job requirements."
            )
        if edu_score < 0.5:
            suggestions.append(
                "Highlight relevant certifications, courses, or continuing education."
            )
        if skill_score >= 0.8 and kw_score >= 0.6 and not suggestions:
            suggestions.append(
                "Your resume is well-aligned. Consider tailoring your summary statement."
            )
        return suggestions
