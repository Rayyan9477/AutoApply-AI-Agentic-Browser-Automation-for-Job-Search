"""ATS optimization engine for resume improvement suggestions.

Analyzes a scored resume and provides targeted suggestions to improve
ATS compatibility, keyword coverage, and overall match quality.
"""

from __future__ import annotations

import structlog

from app.core.ats.scorer import ScoreDetails
from app.core.ats.skill_matcher import SkillMatcher

logger = structlog.get_logger(__name__)

# Industry-specific keywords with importance weights (0-1).
# Ported verbatim from v1 resume_optimizer.py lines 130-177.
_INDUSTRY_KEYWORDS: dict[str, dict[str, float]] = {
    "software_engineering": {
        "agile": 0.8, "scrum": 0.7, "ci/cd": 0.9, "devops": 0.8,
        "microservices": 0.85, "api": 0.9, "rest": 0.8, "graphql": 0.7,
        "cloud": 0.85, "aws": 0.8, "docker": 0.85, "kubernetes": 0.8,
        "testing": 0.9, "unit testing": 0.8, "integration testing": 0.75,
        "code review": 0.7, "git": 0.9, "system design": 0.85,
        "scalability": 0.8, "performance": 0.75, "security": 0.7,
        "monitoring": 0.7, "logging": 0.65, "debugging": 0.7,
    },
    "data_science": {
        "machine learning": 0.95, "deep learning": 0.85, "nlp": 0.8,
        "computer vision": 0.75, "statistics": 0.9, "python": 0.95,
        "r": 0.7, "sql": 0.85, "tensorflow": 0.8, "pytorch": 0.8,
        "pandas": 0.85, "numpy": 0.8, "scikit-learn": 0.85,
        "data visualization": 0.75, "feature engineering": 0.8,
        "model evaluation": 0.8, "a/b testing": 0.7, "etl": 0.75,
        "big data": 0.7, "spark": 0.7, "hadoop": 0.6,
    },
    "product_management": {
        "roadmap": 0.9, "strategy": 0.85, "stakeholder management": 0.85,
        "user research": 0.8, "data-driven": 0.8, "analytics": 0.8,
        "kpi": 0.75, "okr": 0.7, "agile": 0.85, "scrum": 0.75,
        "prioritization": 0.85, "go-to-market": 0.7, "mvp": 0.75,
        "user stories": 0.8, "competitive analysis": 0.7,
        "market research": 0.7, "customer feedback": 0.75,
    },
    "devops": {
        "ci/cd": 0.95, "docker": 0.9, "kubernetes": 0.9, "terraform": 0.85,
        "ansible": 0.75, "jenkins": 0.7, "github actions": 0.75,
        "monitoring": 0.85, "prometheus": 0.75, "grafana": 0.7,
        "aws": 0.85, "gcp": 0.8, "azure": 0.8, "linux": 0.9,
        "networking": 0.75, "security": 0.8, "iac": 0.8,
        "observability": 0.8, "sre": 0.75, "incident management": 0.7,
    },
    "cybersecurity": {
        "penetration testing": 0.9, "vulnerability assessment": 0.9,
        "siem": 0.8, "soc": 0.8, "incident response": 0.85,
        "encryption": 0.8, "firewall": 0.75, "ids/ips": 0.75,
        "compliance": 0.8, "risk assessment": 0.85, "threat modeling": 0.85,
        "zero trust": 0.7, "devsecops": 0.75, "owasp": 0.8,
        "forensics": 0.7, "malware analysis": 0.7,
    },
    "cloud_engineering": {
        "aws": 0.9, "gcp": 0.85, "azure": 0.85, "terraform": 0.9,
        "cloudformation": 0.75, "serverless": 0.8, "lambda": 0.75,
        "ec2": 0.7, "s3": 0.7, "vpc": 0.7, "load balancing": 0.75,
        "auto scaling": 0.75, "cost optimization": 0.7,
        "multi-cloud": 0.65, "hybrid cloud": 0.65,
    },
}

# Formatting and structure tips for ATS compatibility.
_FORMAT_SUGGESTIONS: list[str] = [
    "Use standard section headings (Experience, Education, Skills).",
    "Avoid tables, columns, and text boxes that confuse ATS parsers.",
    "Use a clean, single-column layout with consistent formatting.",
    "Include both spelled-out and abbreviated forms of key terms "
    "(e.g., 'CI/CD' and 'Continuous Integration').",
    "Quantify achievements with numbers and percentages where possible.",
]


class ATSOptimizer:
    """Suggests ATS optimization improvements for resumes.

    Analyzes scoring results and resume content to produce actionable
    suggestions for improving ATS pass-through rates.

    Args:
        skill_matcher: Injected SkillMatcher for skill gap analysis.
    """

    INDUSTRY_KEYWORDS: dict[str, dict[str, float]] = _INDUSTRY_KEYWORDS

    def __init__(self, skill_matcher: SkillMatcher) -> None:
        self._skill_matcher = skill_matcher
        logger.info("ats_optimizer.initialized")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def suggest_improvements(
        self,
        score_details: ScoreDetails,
        resume_text: str,
        job_description: str,
    ) -> list[str]:
        """Generate a prioritized list of improvement suggestions.

        Args:
            score_details: Result from ResumeScorer.score_resume().
            resume_text: Full text of the candidate resume.
            job_description: Full text of the job posting.

        Returns:
            Ordered list of actionable improvement suggestions.
        """
        suggestions: list[str] = []

        # Skill gap suggestions
        suggestions.extend(
            self._skill_gap_suggestions(score_details),
        )

        # Industry keyword suggestions
        industry = self.detect_industry(job_description)
        if industry:
            missing_kw = self.get_missing_keywords(resume_text, industry)
            if missing_kw:
                top = missing_kw[:5]
                suggestions.append(
                    f"Add industry-relevant keywords: {', '.join(top)}"
                )

        # Keyword density suggestions
        if score_details.keyword_score < 0.3:
            suggestions.append(
                "Your resume has low keyword overlap with the job description. "
                "Mirror the exact terminology used in the posting."
            )

        # Experience suggestions
        if score_details.experience_score < 0.5:
            suggestions.append(
                "Strengthen your experience section by emphasizing "
                "responsibilities and achievements that align with the "
                "job requirements."
            )

        # Education suggestions
        if score_details.education_score < 0.5:
            suggestions.append(
                "Consider adding relevant certifications, bootcamps, "
                "or online courses to strengthen your education profile."
            )

        # Formatting suggestions
        suggestions.extend(self._format_suggestions(resume_text))

        # Carry over scorer-generated suggestions that are not duplicates
        existing = set(suggestions)
        for s in score_details.improvement_suggestions:
            if s not in existing:
                suggestions.append(s)

        logger.info(
            "ats_optimizer.suggestions_generated",
            count=len(suggestions),
            industry=industry,
        )
        return suggestions

    def detect_industry(self, job_description: str) -> str:
        """Detect the most likely industry from a job description.

        Args:
            job_description: Full text of the job posting.

        Returns:
            Industry key from INDUSTRY_KEYWORDS, or empty string if
            no confident match is found.
        """
        lower = job_description.lower()
        best_industry = ""
        best_score = 0.0

        for industry, keywords in _INDUSTRY_KEYWORDS.items():
            score = sum(
                weight for kw, weight in keywords.items() if kw in lower
            )
            if score > best_score:
                best_score = score
                best_industry = industry

        # Require a minimum confidence threshold.
        if best_score < 1.5:
            return ""

        logger.debug(
            "ats_optimizer.industry_detected",
            industry=best_industry,
            confidence=round(best_score, 2),
        )
        return best_industry

    def get_missing_keywords(
        self,
        resume_text: str,
        industry: str,
    ) -> list[str]:
        """Find high-value industry keywords missing from a resume.

        Args:
            resume_text: Full text of the candidate resume.
            industry: Industry key from INDUSTRY_KEYWORDS.

        Returns:
            List of missing keywords sorted by importance (descending).
        """
        keywords = _INDUSTRY_KEYWORDS.get(industry, {})
        if not keywords:
            return []

        lower = resume_text.lower()
        missing: list[tuple[str, float]] = []
        for keyword, weight in keywords.items():
            if keyword not in lower:
                missing.append((keyword, weight))

        # Sort by weight descending.
        missing.sort(key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in missing]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _skill_gap_suggestions(self, score_details: ScoreDetails) -> list[str]:
        """Generate suggestions for closing skill gaps."""
        suggestions: list[str] = []

        if score_details.missing_required_skills:
            skills = score_details.missing_required_skills
            if len(skills) <= 3:
                suggestions.append(
                    f"Critical: add required skills to your resume: "
                    f"{', '.join(skills)}"
                )
            else:
                top = skills[:3]
                suggestions.append(
                    f"Critical: add these required skills (and "
                    f"{len(skills) - 3} more): {', '.join(top)}"
                )

        if score_details.missing_preferred_skills:
            skills = score_details.missing_preferred_skills[:3]
            suggestions.append(
                f"Recommended: highlight preferred skills if applicable: "
                f"{', '.join(skills)}"
            )

        # Suggest similar skills the candidate might already have.
        for skill in score_details.missing_required_skills[:3]:
            similar = self._skill_matcher.find_similar_skills(skill)
            if similar:
                suggestions.append(
                    f"You may already have equivalent experience for "
                    f"'{skill}' — consider listing: {', '.join(similar[:2])}"
                )

        return suggestions

    def _format_suggestions(self, resume_text: str) -> list[str]:
        """Check for ATS formatting issues and return relevant tips."""
        suggestions: list[str] = []

        # Check for very short resumes
        word_count = len(resume_text.split())
        if word_count < 150:
            suggestions.append(
                "Your resume appears very short. ATS systems favour "
                "detailed resumes with 400-800 words."
            )

        # Check for missing standard sections
        lower = resume_text.lower()
        expected_sections = ["experience", "education", "skills"]
        missing = [s for s in expected_sections if s not in lower]
        if missing:
            suggestions.append(
                f"Add standard sections that may be missing: "
                f"{', '.join(missing).title()}"
            )

        return suggestions
