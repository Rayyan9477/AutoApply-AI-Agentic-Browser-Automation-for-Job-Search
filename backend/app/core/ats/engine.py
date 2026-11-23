"""Shared ATS scoring engine.

The single code path behind résumé scoring (``services.resume``), job analysis
(``services.job_search``) and, through them, the worker's ATS gate. It uses the
process-wide cached spaCy pipeline (:func:`app.core.ats.nlp.get_nlp`), so it never pays
a per-request ``spacy.load``. It also builds a real candidate profile (skills, dated
experience, degrees) instead of the empty experience/education lists the call sites
used to pass.

Synchronous and CPU-bound: async callers should run it in a worker thread.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import structlog

from app.core.ats.experience_analyzer import ExperienceAnalyzer
from app.core.ats.keyword_analyzer import KeywordAnalyzer
from app.core.ats.nlp import get_nlp
from app.core.ats.profile import extract_candidate_profile
from app.core.ats.scorer import ResumeScorer, ScoreDetails
from app.core.ats.skill_matcher import SkillMatcher

if TYPE_CHECKING:
    from app.models.job import Job

logger = structlog.get_logger(__name__)


def score_resume_against_job(resume_text: str, job: Job) -> ScoreDetails:
    """Score résumé text against a stored job listing.

    Args:
        resume_text: Plain résumé text (``Resume.content_text``).
        job: The job listing; ``description`` and ``skills_required`` are read.

    Returns:
        The full :class:`ScoreDetails` breakdown (scores in [0, 1]).
    """
    nlp = get_nlp()
    skill_matcher = SkillMatcher(nlp)
    scorer = ResumeScorer(skill_matcher, KeywordAnalyzer(nlp), ExperienceAnalyzer(nlp))

    job_description = job.description or ""
    profile = extract_candidate_profile(resume_text, skill_matcher)
    metadata = job_metadata(job, skill_matcher)
    logger.debug(
        "ats_engine.profile",
        skills=len(profile["skills"]),
        roles=len(profile["experience"]),
        degrees=len(profile["education"]),
        required_skills=len(metadata["required_skills"]),
    )
    return scorer.score_resume(resume_text, job_description, profile, metadata)


def job_metadata(job: Job, skill_matcher: SkillMatcher) -> dict[str, Any]:
    """Build the scorer's job metadata from ``job.skills_required``.

    Accepts ``{"required": [...], "preferred": [...]}``, the legacy ``{"skills": [...]}``
    shape and a bare list. When the listing carries no skill metadata at all (Exa results,
    for example), the skills recognised in the description become the required set.
    Otherwise every such job would get a flat, neutral 0.5 skill score.
    """
    raw = job.skills_required
    required: list[str] = []
    preferred: list[str] = []
    if isinstance(raw, dict):
        required = list(raw.get("required") or raw.get("skills") or [])
        preferred = list(raw.get("preferred") or [])
    elif isinstance(raw, list):
        required = list(raw)

    if not required and not preferred:
        required = sorted(skill_matcher.extract_skills(job.description or ""))
    return {"required_skills": required, "preferred_skills": preferred}
