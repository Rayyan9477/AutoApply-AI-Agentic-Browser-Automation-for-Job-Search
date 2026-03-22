"""Resume tailoring prompt for LLM-powered resume optimization.

Provides structured output schema matching the Jinja2 template context
and a prompt that instructs the LLM to tailor resume content for a
specific job while preserving factual accuracy.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field


class ExperienceEntry(BaseModel):
    """A single work experience entry."""

    title: str = ""
    company: str = ""
    duration: str = ""
    description: str = ""


class EducationEntry(BaseModel):
    """A single education entry."""

    degree: str = ""
    institution: str = ""
    year: str = ""


class ProjectEntry(BaseModel):
    """A single project entry."""

    name: str = ""
    description: str = ""


class TailoredResumeData(BaseModel):
    """Structured resume data matching the Jinja2 template context.

    This schema is enforced on LLM output to guarantee compatibility
    with all five resume templates (modern, classic, creative,
    executive, minimal).
    """

    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    title: str = ""
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)


RESUME_TAILOR_SYSTEM_PROMPT = """\
You are an expert resume writer and career coach. Your task is to \
tailor a candidate's resume for a specific job posting.

RULES:
1. NEVER fabricate experience, skills, or qualifications not present \
in the original resume.
2. Rewrite the professional summary to target the specific role.
3. Reorder and emphasize skills that match the job requirements.
4. Rewrite experience bullet points to highlight achievements and \
responsibilities relevant to the target job.
5. Use strong action verbs and quantify achievements where the \
original data supports it.
6. Preserve ALL factual content — dates, company names, degrees, \
and certifications must remain unchanged.
7. Use industry-standard terminology from the job posting where it \
accurately describes the candidate's experience.
8. Return ONLY valid JSON matching the required schema."""


def render_resume_tailor_prompt(
    resume_data: dict,
    job_description: str,
) -> str:
    """Build the user prompt for resume tailoring.

    Args:
        resume_data: Structured resume data dict (template context format).
        job_description: Full text of the target job posting.

    Returns:
        Formatted prompt string for LLM completion.
    """
    resume_json = json.dumps(resume_data, indent=2, default=str)

    return f"""\
Tailor the following resume for the job posting below.

CURRENT RESUME DATA:
{resume_json}

TARGET JOB POSTING:
{job_description}

Instructions:
- Rewrite the "summary" field to directly address this role.
- Reorder "skills" so the most relevant ones appear first.
- In each experience entry's "description" field, rewrite the bullet \
points (newline-separated) to emphasize relevant achievements.
- Keep "name", "email", "phone", "location", "linkedin", "github" \
unchanged.
- Keep all "company", "duration", "degree", "institution", "year" \
values unchanged.
- If the candidate has skills that match the job but are worded \
differently, use the job posting's terminology.

Return the complete tailored resume as a JSON object."""
