"""Unit tests for app.core.llm.prompts.cover_letter."""

from __future__ import annotations

from app.core.llm.prompts.cover_letter import (
    TEMPLATE_PROMPTS,
    CoverLetterTemplate,
    render_prompt,
    select_best_template,
)

# ---------------------------------------------------------------------------
# select_best_template
# ---------------------------------------------------------------------------


class TestSelectBestTemplate:
    def test_referral_takes_priority(self) -> None:
        result = select_best_template(
            job_title="CTO",
            job_description="technical leader",
            is_career_change=True,
            has_referral=True,
        )
        assert result == CoverLetterTemplate.REFERRAL

    def test_career_change_takes_priority_over_title(self) -> None:
        result = select_best_template(
            job_title="Software Engineer",
            job_description="build things",
            is_career_change=True,
        )
        assert result == CoverLetterTemplate.CAREER_CHANGE

    def test_executive_title_returns_executive(self) -> None:
        result = select_best_template("VP of Engineering", "lead teams")
        assert result == CoverLetterTemplate.EXECUTIVE

    def test_technical_title_returns_technical(self) -> None:
        result = select_best_template("Senior Software Engineer", "build APIs")
        assert result == CoverLetterTemplate.TECHNICAL

    def test_creative_title_returns_creative(self) -> None:
        result = select_best_template("UX Designer", "design experiences")
        assert result == CoverLetterTemplate.CREATIVE

    def test_generic_title_returns_standard(self) -> None:
        result = select_best_template("Office Manager", "manage office operations")
        assert result == CoverLetterTemplate.STANDARD


# ---------------------------------------------------------------------------
# TEMPLATE_PROMPTS completeness
# ---------------------------------------------------------------------------


class TestTemplatePrompts:
    def test_all_enum_values_have_prompts(self) -> None:
        for template in CoverLetterTemplate:
            assert template in TEMPLATE_PROMPTS, f"Missing prompt for {template}"

    def test_all_prompts_contain_placeholders(self) -> None:
        for template, prompt in TEMPLATE_PROMPTS.items():
            assert "{job_description}" in prompt, f"{template} missing job_description"
            assert "{candidate_resume}" in prompt, f"{template} missing candidate_resume"


# ---------------------------------------------------------------------------
# render_prompt
# ---------------------------------------------------------------------------


class TestRenderPrompt:
    def test_substitutes_job_and_resume(self) -> None:
        result = render_prompt(
            CoverLetterTemplate.STANDARD,
            job_description="Build APIs",
            candidate_resume="5 years Python",
        )
        assert "Build APIs" in result
        assert "5 years Python" in result

    def test_includes_company_info_when_provided(self) -> None:
        result = render_prompt(
            CoverLetterTemplate.STANDARD,
            job_description="desc",
            candidate_resume="resume",
            company_info="Acme Corp is a leader in widgets",
        )
        assert "Acme Corp" in result

    def test_referral_template_includes_referral_info(self) -> None:
        result = render_prompt(
            CoverLetterTemplate.REFERRAL,
            job_description="desc",
            candidate_resume="resume",
            referral_info="Referred by Jane Smith",
        )
        assert "Jane Smith" in result

    def test_referral_template_default_when_no_info(self) -> None:
        result = render_prompt(
            CoverLetterTemplate.REFERRAL,
            job_description="desc",
            candidate_resume="resume",
        )
        assert "No referral details provided" in result
