"""Cover letter prompt templates for LLM generation.

Provides six distinct cover letter styles, automatic template selection
based on job context, and a renderer that injects candidate/job data
into the chosen prompt.
"""

from enum import StrEnum


class CoverLetterTemplate(StrEnum):
    """Available cover letter template styles."""

    STANDARD = "standard"
    TECHNICAL = "technical"
    CREATIVE = "creative"
    EXECUTIVE = "executive"
    CAREER_CHANGE = "career_change"
    REFERRAL = "referral"


PROMPT_STANDARD = """\
Write a professional cover letter for the following job posting.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{candidate_resume}

{company_section}

Instructions:
- Address the hiring manager professionally (use "Dear Hiring Manager" if name unknown)
- Open with a strong hook that connects the candidate's experience to the role
- Highlight 2-3 key achievements from the resume that directly match the job requirements
- Show genuine enthusiasm for the company and the specific role
- Close with a confident call to action requesting an interview
- Keep the tone professional yet personable
- Limit to 3-4 concise paragraphs (250-350 words total)
- Do NOT fabricate experience or skills not present in the resume
"""

PROMPT_TECHNICAL = """\
Write a technical cover letter for the following engineering/technical role.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{candidate_resume}

{company_section}

Instructions:
- Lead with the candidate's most relevant technical expertise for this role
- Reference specific technologies, frameworks, and tools from both the resume and job posting
- Include a concrete example of a technical problem solved or system built, with measurable impact
- Demonstrate understanding of the company's technical stack or engineering challenges
- Mention relevant open-source contributions, publications, or side projects
- Show passion for engineering craft (code quality, scalability, testing, architecture)
- Keep the tone technically confident but not arrogant
- Limit to 3-4 focused paragraphs (250-400 words total)
- Do NOT fabricate technical skills or projects not present in the resume
"""

PROMPT_CREATIVE = """\
Write a creative and engaging cover letter for the following role.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{candidate_resume}

{company_section}

Instructions:
- Open with a compelling story, bold statement, or creative hook that captures attention
- Show personality and authentic voice while remaining professional
- Connect the candidate's unique background and experiences to the role's needs
- Demonstrate creative thinking and problem-solving ability through specific examples
- Express genuine passion for the industry, company mission, or product
- End with a memorable closing that reinforces the candidate's unique value proposition
- Balance creativity with substance — every sentence should serve a purpose
- Limit to 3-4 paragraphs (250-400 words total)
- Do NOT fabricate experience or skills not present in the resume
"""

PROMPT_EXECUTIVE = """\
Write an executive-level cover letter for the following senior leadership role.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{candidate_resume}

{company_section}

Instructions:
- Open with a high-impact statement about the candidate's leadership brand and vision
- Emphasize strategic impact: revenue growth, organizational transformation, market expansion
- Quantify achievements with specific metrics (revenue, team size, market share, cost savings)
- Demonstrate board-level thinking and cross-functional leadership experience
- Reference industry trends and how the candidate is positioned to address them
- Show understanding of the company's strategic challenges and growth trajectory
- Convey executive gravitas — confident, concise, forward-looking
- Limit to 3-4 paragraphs (300-400 words total)
- Do NOT fabricate achievements or metrics not supported by the resume
"""

PROMPT_CAREER_CHANGE = """\
Write a compelling cover letter for a candidate transitioning into a new career field.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{candidate_resume}

{company_section}

Instructions:
- Acknowledge the career transition directly and frame it as a deliberate, strategic move
- Identify and emphasize transferable skills from the candidate's previous career
- Draw clear parallels between past accomplishments and the requirements of the new role
- Highlight any relevant education, certifications, bootcamps, or self-directed learning
- Show genuine passion and proactive steps taken toward the new field
- Address the "why" — explain what draws the candidate to this new direction
- Demonstrate that diverse experience brings unique perspective and value
- Convey confidence without dismissing the learning curve ahead
- Limit to 3-4 paragraphs (300-400 words total)
- Do NOT fabricate experience, certifications, or training not present in the resume
"""

PROMPT_REFERRAL = """\
Write a cover letter for a candidate who has been referred to the position.

JOB DESCRIPTION:
{job_description}

CANDIDATE RESUME:
{candidate_resume}

{company_section}

REFERRAL INFORMATION:
{referral_info}

Instructions:
- Open by mentioning the referral prominently in the first sentence
- Briefly explain the relationship with the referrer and what they shared about the role
- Transition naturally into the candidate's relevant qualifications and achievements
- Show that the candidate has done independent research beyond the referral connection
- Highlight 2-3 specific strengths that align with the role's requirements
- Express enthusiasm for the team and company culture informed by the referral's insights
- Close with a call to action that leverages the referral connection
- Keep the tone warm and collegial while remaining professional
- Limit to 3-4 paragraphs (250-350 words total)
- Do NOT fabricate details about the referral relationship
"""

TEMPLATE_PROMPTS: dict[CoverLetterTemplate, str] = {
    CoverLetterTemplate.STANDARD: PROMPT_STANDARD,
    CoverLetterTemplate.TECHNICAL: PROMPT_TECHNICAL,
    CoverLetterTemplate.CREATIVE: PROMPT_CREATIVE,
    CoverLetterTemplate.EXECUTIVE: PROMPT_EXECUTIVE,
    CoverLetterTemplate.CAREER_CHANGE: PROMPT_CAREER_CHANGE,
    CoverLetterTemplate.REFERRAL: PROMPT_REFERRAL,
}


def select_best_template(
    job_title: str,
    job_description: str,
    is_career_change: bool = False,
    has_referral: bool = False,
) -> CoverLetterTemplate:
    """Select the best cover letter template based on job context.

    Args:
        job_title: The job title from the listing.
        job_description: Full job description text.
        is_career_change: Whether the candidate is changing careers.
        has_referral: Whether the candidate has a referral.

    Returns:
        The most appropriate ``CoverLetterTemplate`` for the context.
    """
    if has_referral:
        return CoverLetterTemplate.REFERRAL

    if is_career_change:
        return CoverLetterTemplate.CAREER_CHANGE

    title_lower = job_title.lower()
    desc_lower = job_description.lower()

    executive_keywords = {
        "vp", "vice president", "director", "chief", "head of",
        "cto", "ceo", "cfo", "coo", "svp", "evp", "partner",
        "president", "managing director",
    }
    if any(kw in title_lower for kw in executive_keywords):
        return CoverLetterTemplate.EXECUTIVE

    technical_keywords = {
        "engineer", "developer", "architect", "devops", "sre",
        "data scientist", "machine learning", "software", "backend",
        "frontend", "fullstack", "full-stack", "platform", "infrastructure",
        "security engineer", "cloud engineer", "mlops",
    }
    if any(kw in title_lower for kw in technical_keywords):
        return CoverLetterTemplate.TECHNICAL

    creative_keywords = {
        "designer", "creative", "content", "copywriter", "brand",
        "ux", "ui", "art director", "marketing", "social media",
        "storytelling", "editorial",
    }
    if any(kw in title_lower or kw in desc_lower for kw in creative_keywords):
        return CoverLetterTemplate.CREATIVE

    return CoverLetterTemplate.STANDARD


def render_prompt(
    template: CoverLetterTemplate,
    job_description: str,
    candidate_resume: str,
    company_info: str = "",
    referral_info: str = "",
) -> str:
    """Render a cover letter prompt with the given context.

    Args:
        template: The cover letter template style to use.
        job_description: Full job description text.
        candidate_resume: Candidate's resume text.
        company_info: Optional company background information.
        referral_info: Optional referral details (required for REFERRAL template).

    Returns:
        Fully rendered prompt string ready for LLM completion.
    """
    company_section = (
        f"COMPANY INFORMATION:\n{company_info}" if company_info else ""
    )
    prompt_template = TEMPLATE_PROMPTS[template]

    kwargs: dict[str, str] = {
        "job_description": job_description,
        "candidate_resume": candidate_resume,
        "company_section": company_section,
    }
    if template == CoverLetterTemplate.REFERRAL:
        kwargs["referral_info"] = referral_info or "No referral details provided."

    return prompt_template.format(**kwargs)
