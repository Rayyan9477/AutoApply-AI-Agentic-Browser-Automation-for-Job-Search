"""Resume management service.

Handles upload, listing, generation, and scoring of resumes.
Uses DocumentParser for real file parsing and SkillMatcher for skill extraction.
"""

import uuid
from pathlib import Path

import structlog
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.documents.parser import DocumentParser, ParsedResume
from app.core.exceptions import ParseError, RecordNotFoundError
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.resume import (
    ResumeGenerateRequest,
    ResumeListResponse,
    ResumeResponse,
    ResumeScoreRequest,
    ResumeScoreResponse,
    ResumeUploadResponse,
)

logger = structlog.get_logger(__name__)

UPLOAD_DIR = Path("data/uploads")

_parser = DocumentParser()


def _extract_skills_text_based(text: str) -> list[str]:
    """Extract skills using the SkillMatcher text-based approach.

    Falls back gracefully if spaCy is not available by using only
    the regex-based word matching in SkillMatcher.extract_skills.
    """
    try:
        from app.core.ats.skill_matcher import SKILL_VARIATIONS

        lower = text.lower()
        import re

        found: list[str] = []
        seen: set[str] = set()
        for canonical, variations in SKILL_VARIATIONS.items():
            if canonical in seen:
                continue
            if re.search(rf"\b{re.escape(canonical)}\b", lower):
                found.append(canonical)
                seen.add(canonical)
                continue
            for variant in variations:
                if re.search(rf"\b{re.escape(variant)}\b", lower):
                    found.append(canonical)
                    seen.add(canonical)
                    break
        return found
    except Exception:
        logger.warning("skill_extraction_fallback_failed")
        return []


def _extract_skills(text: str) -> list[str]:
    """Extract skills, trying spaCy-backed SkillMatcher first, then text-only."""
    try:
        import spacy

        from app.core.ats.skill_matcher import SkillMatcher

        nlp = spacy.load("en_core_web_sm")
        matcher = SkillMatcher(nlp)
        return sorted(matcher.extract_skills(text))
    except Exception:
        logger.info("spacy_unavailable_using_text_extraction")
        return _extract_skills_text_based(text)


async def upload_resume(
    db: AsyncSession,
    file: UploadFile,
) -> ResumeUploadResponse:
    """Upload, parse, and store a resume file.

    Saves the file to disk, parses it with DocumentParser to extract
    text, then uses SkillMatcher for skill detection.

    Args:
        db: Async database session.
        file: Uploaded resume file.

    Returns:
        Upload response with detected metadata.
    """
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_ext = Path(file.filename or "resume.pdf").suffix.lower()
    file_id = uuid.uuid4().hex
    dest = UPLOAD_DIR / f"{file_id}{file_ext}"

    content = await file.read()
    dest.write_bytes(content)

    # Parse the document for real text extraction
    parsed_text = ""
    word_count = 0
    skills_detected: list[str] = []

    try:
        parsed: ParsedResume = await _parser.parse(dest)
        parsed_text = parsed.raw_text
        word_count = parsed.word_count
        skills_detected = _extract_skills(parsed_text)
        logger.info(
            "resume_parsed_successfully",
            file=file.filename,
            word_count=word_count,
            skills_count=len(skills_detected),
        )
    except (ParseError, Exception) as exc:
        # Parsing failed -- still save the record but with raw byte-decoded text
        logger.warning(
            "resume_parse_failed_using_fallback",
            file=file.filename,
            error=str(exc),
        )
        parsed_text = content.decode("utf-8", errors="ignore")
        word_count = len(parsed_text.split())
        # Try skill extraction on the raw text anyway
        skills_detected = _extract_skills(parsed_text)

    resume = Resume(
        name=file.filename or "Untitled Resume",
        type="base",
        template_id="modern",
        file_path_pdf=str(dest) if file_ext == ".pdf" else None,
        file_path_docx=str(dest) if file_ext == ".docx" else None,
        content_text=parsed_text[:5000],
    )
    db.add(resume)
    await db.commit()
    await db.refresh(resume)

    logger.info("resume_uploaded", resume_id=resume.id, filename=file.filename)

    return ResumeUploadResponse(
        id=resume.id,
        name=resume.name,
        file_format=file_ext.lstrip("."),
        word_count=word_count,
        skills_detected=skills_detected,
    )


async def list_resumes(db: AsyncSession) -> ResumeListResponse:
    """List all resumes.

    Args:
        db: Async database session.

    Returns:
        List of all resumes with total count.
    """
    result = await db.execute(select(Resume).order_by(Resume.created_at.desc()))
    resumes = list(result.scalars().all())
    items = [ResumeResponse.model_validate(r) for r in resumes]
    return ResumeListResponse(items=items, total=len(items))


async def get_resume(db: AsyncSession, resume_id: str) -> Resume:
    """Get a resume by ID or raise RecordNotFoundError."""
    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise RecordNotFoundError("Resume", resume_id)
    return resume


async def _get_job(db: AsyncSession, job_id: str) -> Job:
    """Get a job by ID or raise RecordNotFoundError."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise RecordNotFoundError("Job", job_id)
    return job


async def generate_tailored_resume(
    db: AsyncSession,
    request: ResumeGenerateRequest,
) -> ResumeResponse:
    """Generate a tailored resume for a specific job.

    Placeholder: returns a stub record. Real LLM generation in Phase 5.

    Args:
        db: Async database session.
        request: Generation parameters.

    Returns:
        The generated resume response.
    """
    base = await get_resume(db, request.base_resume_id)

    tailored = Resume(
        name=f"Tailored - {base.name}",
        type="tailored",
        template_id=request.template_id,
        base_resume_id=request.base_resume_id,
        job_id=request.job_id,
    )
    db.add(tailored)
    await db.commit()
    await db.refresh(tailored)

    logger.info(
        "tailored_resume_generated",
        resume_id=tailored.id,
        base_id=request.base_resume_id,
        job_id=request.job_id,
    )
    return ResumeResponse.model_validate(tailored)


async def score_resume(
    db: AsyncSession,
    resume_id: str,
    request: ResumeScoreRequest,
) -> ResumeScoreResponse:
    """Score a resume against a job listing using multi-factor ATS analysis.

    Loads the resume text and job description from the database, then
    uses ResumeScorer for real scoring. Falls back to a basic keyword
    overlap score if spaCy is not available.

    Args:
        db: Async database session.
        resume_id: UUID of the resume.
        request: Scoring request with target job ID.

    Returns:
        Detailed ATS score breakdown.
    """
    resume = await get_resume(db, resume_id)
    job = await _get_job(db, request.job_id)

    resume_text = resume.content_text or ""
    job_description = job.description or ""

    if not resume_text.strip():
        logger.warning("score_resume_empty_text", resume_id=resume_id)
        return ResumeScoreResponse(
            resume_id=resume_id,
            job_id=request.job_id,
            overall_score=0.0,
            skill_score=0.0,
            experience_score=0.0,
            education_score=0.0,
            keyword_score=0.0,
            missing_skills=["Resume has no parsed text content"],
            suggestions=["Re-upload your resume to enable parsing"],
        )

    try:
        return _score_with_full_engine(
            resume_id, request.job_id, resume_text, job_description, job,
        )
    except Exception as exc:
        logger.warning(
            "full_scoring_failed_using_fallback",
            error=str(exc),
        )
        return _score_with_text_fallback(
            resume_id, request.job_id, resume_text, job_description,
        )


def _score_with_full_engine(
    resume_id: str,
    job_id: str,
    resume_text: str,
    job_description: str,
    job: Job,
) -> ResumeScoreResponse:
    """Score using the full ResumeScorer with spaCy."""
    import spacy

    from app.core.ats.experience_analyzer import ExperienceAnalyzer
    from app.core.ats.keyword_analyzer import KeywordAnalyzer
    from app.core.ats.scorer import ResumeScorer
    from app.core.ats.skill_matcher import SkillMatcher

    nlp = spacy.load("en_core_web_sm")
    skill_matcher = SkillMatcher(nlp)
    keyword_analyzer = KeywordAnalyzer(nlp)
    experience_analyzer = ExperienceAnalyzer(nlp)
    scorer = ResumeScorer(skill_matcher, keyword_analyzer, experience_analyzer)

    # Build candidate profile from resume text
    candidate_skills = sorted(skill_matcher.extract_skills(resume_text))
    candidate_profile = {
        "skills": candidate_skills,
        "experience": [],
        "education": [],
    }

    # Build job metadata from the Job model
    required_skills: list[str] = []
    preferred_skills: list[str] = []
    if job.skills_required and isinstance(job.skills_required, dict):
        required_skills = job.skills_required.get("required", [])
        preferred_skills = job.skills_required.get("preferred", [])
    job_metadata = {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
    }

    details = scorer.score_resume(
        resume_text, job_description, candidate_profile, job_metadata,
    )

    return ResumeScoreResponse(
        resume_id=resume_id,
        job_id=job_id,
        overall_score=details.overall_score,
        skill_score=details.skill_score,
        experience_score=details.experience_score,
        education_score=details.education_score,
        keyword_score=details.keyword_score,
        missing_skills=details.missing_required_skills,
        suggestions=details.improvement_suggestions,
    )


def _score_with_text_fallback(
    resume_id: str,
    job_id: str,
    resume_text: str,
    job_description: str,
) -> ResumeScoreResponse:
    """Basic keyword overlap scoring when spaCy is unavailable."""
    resume_skills = set(_extract_skills(resume_text))
    job_skills = set(_extract_skills(job_description))

    if job_skills:
        matched = resume_skills & job_skills
        skill_score = len(matched) / len(job_skills)
        missing = sorted(job_skills - resume_skills)
    else:
        skill_score = 0.5
        missing = []

    # Simple keyword overlap
    resume_words = set(resume_text.lower().split())
    job_words = set(job_description.lower().split()) - {
        "the", "a", "an", "is", "are", "and", "or", "to", "in", "of", "for",
        "with", "on", "at", "by", "from", "as", "we", "you", "your", "our",
    }
    keyword_score = len(resume_words & job_words) / len(job_words) if job_words else 0.0

    overall = 0.5 * skill_score + 0.5 * min(keyword_score, 1.0)

    suggestions: list[str] = []
    if missing:
        suggestions.append(
            f"Add these skills to your resume: {', '.join(missing[:5])}"
        )
    if keyword_score < 0.4:
        suggestions.append(
            "Mirror more terminology from the job description in your resume."
        )

    return ResumeScoreResponse(
        resume_id=resume_id,
        job_id=job_id,
        overall_score=round(overall, 4),
        skill_score=round(skill_score, 4),
        experience_score=0.0,
        education_score=0.0,
        keyword_score=round(min(keyword_score, 1.0), 4),
        missing_skills=missing,
        suggestions=suggestions,
    )
