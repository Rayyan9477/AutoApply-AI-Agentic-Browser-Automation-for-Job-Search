"""Document generation orchestrator.

Coordinates resume and cover letter generation through the full
pipeline: base data -> optional LLM tailoring -> parallel render
to PDF + DOCX formats.
"""

from __future__ import annotations

import asyncio
import uuid
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict

from app.core.documents.docx_renderer import DOCXRenderer
from app.core.documents.pdf_renderer import PDFRenderer
from app.core.exceptions import GenerationError
from app.core.llm.client import LLMClient
from app.core.llm.prompts.cover_letter import (
    CoverLetterTemplate,
    render_prompt,
    select_best_template,
)

logger = structlog.get_logger(__name__)

OUTPUT_DIR = Path("data/generated")


class GeneratedDocument(BaseModel):
    """Result of a document generation operation.

    Attributes:
        document_id: Unique identifier for this generation run.
        type: Document type (``"resume"`` or ``"cover_letter"``).
        template: Template name that was used.
        pdf_path: Filesystem path to the generated PDF, if produced.
        docx_path: Filesystem path to the generated DOCX, if produced.
    """

    model_config = ConfigDict(frozen=True)

    document_id: str
    type: str
    template: str
    pdf_path: str | None = None
    docx_path: str | None = None


class DocumentGenerator:
    """Orchestrates resume and cover letter generation.

    Pipeline: base data -> LLM tailoring -> parallel render (PDF + DOCX).

    Args:
        llm_client: Optional LLM client for content tailoring.
        output_dir: Root directory for generated documents.
        templates_dir: Root directory containing HTML/CSS templates.
    """

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        output_dir: Path = OUTPUT_DIR,
        templates_dir: Path = Path("templates"),
    ) -> None:
        self._pdf = PDFRenderer(templates_dir=templates_dir)
        self._docx = DOCXRenderer()
        self._llm = llm_client
        self._output_dir = output_dir
        self._templates_dir = templates_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)

    async def generate_resume(
        self,
        resume_data: dict[str, Any],
        job_description: str,
        template_name: str = "modern",
        formats: list[str] | None = None,
    ) -> GeneratedDocument:
        """Generate a tailored resume in specified formats.

        Args:
            resume_data: Structured resume data (name, experience,
                skills, education, etc.).
            job_description: Target job description for LLM tailoring.
            template_name: Resume template to use.
            formats: Output formats (default: ``["pdf", "docx"]``).

        Returns:
            ``GeneratedDocument`` with paths to rendered files.

        Raises:
            GenerationError: If all requested formats fail to render.
        """
        formats = formats or ["pdf", "docx"]
        doc_id = uuid.uuid4().hex[:12]

        # Optionally tailor content via LLM
        context = resume_data
        if self._llm and job_description:
            context = await self._tailor_resume(resume_data, job_description)

        # Render requested formats in parallel
        tasks: list[asyncio.Task[Path]] = []
        task_formats: list[str] = []

        if "pdf" in formats:
            pdf_out = self._output_dir / "resumes" / f"{doc_id}.pdf"
            tasks.append(
                asyncio.ensure_future(
                    self._pdf.render(template_name, context, pdf_out),
                ),
            )
            task_formats.append("pdf")

        if "docx" in formats:
            docx_out = self._output_dir / "resumes" / f"{doc_id}.docx"
            tasks.append(
                asyncio.ensure_future(
                    self._docx.render(template_name, context, docx_out),
                ),
            )
            task_formats.append("docx")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        pdf_path: str | None = None
        docx_path: str | None = None

        for fmt, result in zip(task_formats, results, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    "document_render_error",
                    format=fmt,
                    template=template_name,
                    error=str(result),
                )
            elif isinstance(result, Path):
                if fmt == "pdf":
                    pdf_path = str(result)
                else:
                    docx_path = str(result)

        if not pdf_path and not docx_path:
            raise GenerationError(
                f"All formats failed for resume generation (doc_id={doc_id})",
            )

        logger.info(
            "resume_generated",
            document_id=doc_id,
            template=template_name,
            has_pdf=pdf_path is not None,
            has_docx=docx_path is not None,
        )
        return GeneratedDocument(
            document_id=doc_id,
            type="resume",
            template=template_name,
            pdf_path=pdf_path,
            docx_path=docx_path,
        )

    async def generate_cover_letter(
        self,
        resume_text: str,
        job_description: str,
        company_info: str = "",
        template: CoverLetterTemplate | None = None,
        formats: list[str] | None = None,
    ) -> GeneratedDocument:
        """Generate a cover letter using LLM and render to PDF/DOCX.

        Args:
            resume_text: Candidate's resume as plain text.
            job_description: Full job description text.
            company_info: Optional company background information.
            template: Cover letter style; auto-selected if ``None``.
            formats: Output formats (default: ``["pdf", "docx"]``).

        Returns:
            ``GeneratedDocument`` with paths to rendered files.

        Raises:
            GenerationError: If LLM generation or all renders fail.
        """
        formats = formats or ["pdf", "docx"]
        doc_id = uuid.uuid4().hex[:12]

        # Select template
        if template is None:
            template = select_best_template(
                job_title="",
                job_description=job_description,
            )

        # Generate content via LLM
        content = await self._generate_letter_content(
            template, job_description, resume_text, company_info,
        )

        # Render in parallel
        tasks: list[asyncio.Task[Path]] = []
        task_formats: list[str] = []

        if "pdf" in formats:
            pdf_out = self._output_dir / "cover_letters" / f"{doc_id}.pdf"
            tasks.append(
                asyncio.ensure_future(
                    self._render_cover_letter_pdf(
                        content, template, pdf_out,
                    ),
                ),
            )
            task_formats.append("pdf")

        if "docx" in formats:
            docx_out = self._output_dir / "cover_letters" / f"{doc_id}.docx"
            tasks.append(
                asyncio.ensure_future(
                    self._docx.render_cover_letter(content, docx_out),
                ),
            )
            task_formats.append("docx")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        pdf_path: str | None = None
        docx_path: str | None = None

        for fmt, result in zip(task_formats, results, strict=False):
            if isinstance(result, Exception):
                logger.error(
                    "cover_letter_render_error",
                    format=fmt,
                    error=str(result),
                )
            elif isinstance(result, Path):
                if fmt == "pdf":
                    pdf_path = str(result)
                else:
                    docx_path = str(result)

        if not pdf_path and not docx_path:
            raise GenerationError(
                f"All formats failed for cover letter (doc_id={doc_id})",
            )

        logger.info(
            "cover_letter_generated",
            document_id=doc_id,
            template=template.value,
            has_pdf=pdf_path is not None,
            has_docx=docx_path is not None,
        )
        return GeneratedDocument(
            document_id=doc_id,
            type="cover_letter",
            template=template.value,
            pdf_path=pdf_path,
            docx_path=docx_path,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _tailor_resume(
        self,
        resume_data: dict[str, Any],
        job_description: str,
    ) -> dict[str, Any]:
        """Use LLM to tailor resume data for the target job.

        Sends the resume data and job description to the LLM with
        structured output enforcement, returning the tailored version
        in template-compatible format.
        """
        if not self._llm:
            logger.warning("resume_tailoring_skipped", reason="no_llm_client")
            return resume_data

        from app.core.llm.prompts.resume_tailor import (
            RESUME_TAILOR_SYSTEM_PROMPT,
            TailoredResumeData,
            render_resume_tailor_prompt,
        )

        prompt = render_resume_tailor_prompt(resume_data, job_description)
        try:
            result = await self._llm.complete_with_structured_output(
                prompt=prompt,
                output_schema=TailoredResumeData,
                system_prompt=RESUME_TAILOR_SYSTEM_PROMPT,
                purpose="resume_tailor",
            )
            tailored = result.model_dump()
            logger.info("resume_tailored_via_llm", skills_count=len(tailored.get("skills", [])))
            return tailored
        except Exception:
            logger.exception("resume_tailoring_failed")
            return resume_data

    async def _generate_letter_content(
        self,
        template: CoverLetterTemplate,
        job_description: str,
        resume_text: str,
        company_info: str,
    ) -> str:
        """Generate cover letter content via LLM."""
        if not self._llm:
            return self._fallback_cover_letter(job_description)

        prompt = render_prompt(
            template, job_description, resume_text, company_info,
        )
        response = await self._llm.complete(
            prompt=prompt, purpose="cover_letter",
        )
        return response.content

    @staticmethod
    def _fallback_cover_letter(job_description: str) -> str:
        """Minimal fallback when no LLM client is available."""
        return (
            "Dear Hiring Manager,\n\n"
            "I am writing to express my strong interest in this position. "
            "My background and skills align well with the requirements "
            "outlined in the job description.\n\n"
            "I look forward to discussing how my experience can contribute "
            "to your team's success.\n\n"
            "Sincerely,\n[Your Name]"
        )

    async def _render_cover_letter_pdf(
        self,
        content: str,
        template: CoverLetterTemplate,
        output_path: Path,
    ) -> Path:
        """Render cover letter text to PDF using a template."""
        template_dir = (
            self._templates_dir / "cover_letter" / template.value
        )

        # Use template if available, otherwise fall back to inline HTML
        if (template_dir / "template.html").exists():
            from jinja2 import Environment, FileSystemLoader, select_autoescape

            env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(["html"]),
            )
            html_tpl = env.get_template("template.html")
            html_content = html_tpl.render(content=content)

            css_path = template_dir / "style.css"
            css_string: str | None = None
            if css_path.exists():
                css_string = css_path.read_text(encoding="utf-8")

            return await self._pdf.render_html_string(
                html_content, output_path, css_string,
            )

        # Inline fallback
        html = (
            "<html><body style='font-family:Georgia,serif;"
            "font-size:12pt;margin:1in;line-height:1.6;'>"
            f"{_text_to_html(content)}</body></html>"
        )
        return await self._pdf.render_html_string(
            html, output_path,
        )


def _text_to_html(text: str) -> str:
    """Convert plain text with double-newline paragraphs to HTML."""
    paragraphs = text.split("\n\n")
    return "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
