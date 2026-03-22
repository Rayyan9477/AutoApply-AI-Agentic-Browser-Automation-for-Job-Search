"""ATS optimization prompt for LLM-powered resume rewriting.

Takes ATS score analysis and improvement suggestions, then instructs
the LLM to rewrite the resume to maximize ATS compatibility while
keeping all content factually accurate.
"""

import json

ATS_OPTIMIZE_SYSTEM_PROMPT = """\
You are an ATS (Applicant Tracking System) optimization specialist. \
Your task is to rewrite a resume to maximize its ATS compatibility \
score for a specific job posting.

RULES:
1. NEVER fabricate experience, skills, or qualifications.
2. Incorporate missing keywords naturally into existing content where \
the candidate genuinely has that experience.
3. Mirror the exact terminology from the job posting.
4. Use standard section headings that ATS systems recognize.
5. Front-load the most relevant skills and experience.
6. Quantify achievements with metrics wherever the data supports it.
7. Ensure every required skill from the job posting is mentioned if \
the candidate has it, even if worded differently in the original.
8. Return ONLY valid JSON matching the required schema."""


def render_ats_optimize_prompt(
    resume_text: str,
    job_description: str,
    score_breakdown: dict,
    suggestions: list[str],
) -> str:
    """Build the user prompt for ATS optimization.

    Args:
        resume_text: Full text of the candidate's current resume.
        job_description: Full text of the target job posting.
        score_breakdown: ATS score details (overall, skill, experience,
            education, keyword scores, missing skills).
        suggestions: Improvement suggestions from ATSOptimizer.

    Returns:
        Formatted prompt string for LLM completion.
    """
    scores_json = json.dumps(score_breakdown, indent=2, default=str)
    suggestions_text = "\n".join(f"- {s}" for s in suggestions)

    return f"""\
Optimize the following resume to maximize its ATS score for the job \
posting below.

CURRENT RESUME:
{resume_text}

TARGET JOB POSTING:
{job_description}

CURRENT ATS SCORE ANALYSIS:
{scores_json}

IMPROVEMENT SUGGESTIONS:
{suggestions_text}

Instructions:
- Address each suggestion above in your rewrite.
- For missing skills: if the candidate has the skill under a different \
name, use the job posting's terminology instead.
- For low keyword scores: weave job-specific keywords into the \
summary and experience descriptions naturally.
- For experience gaps: rewrite bullet points to emphasize the most \
relevant responsibilities and achievements.
- Preserve all dates, company names, degrees, and certifications.
- Keep the same structure: name, contact info, summary, skills, \
experience, education, certifications, projects.

Return the optimized resume as a JSON object."""
