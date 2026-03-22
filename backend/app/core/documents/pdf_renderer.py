"""PDF document renderer using WeasyPrint.

Renders Jinja2 HTML templates to PDF files. All blocking I/O from
WeasyPrint and Jinja2 is offloaded to a thread-pool executor so the
async event loop is never blocked.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import structlog

from app.core.exceptions import GenerationError, TemplateError

logger = structlog.get_logger(__name__)


class PDFRenderer:
    """Renders Jinja2 HTML templates to PDF via WeasyPrint.

    Args:
        templates_dir: Root directory containing template subdirectories.
            Expected layout: ``templates_dir/resume/<name>/template.html``.
    """

    def __init__(self, templates_dir: Path = Path("templates")) -> None:
        self._templates_dir = templates_dir

    async def render(
        self,
        template_name: str,
        context: dict[str, Any],
        output_path: Path,
    ) -> Path:
        """Render an HTML template to PDF.

        Args:
            template_name: Template directory name (e.g. ``"modern"``).
            context: Template variables (name, experience, skills, etc.).
            output_path: Where to save the generated PDF.

        Returns:
            The ``output_path`` on success.

        Raises:
            TemplateError: If the template directory or files are missing.
            GenerationError: If WeasyPrint rendering fails.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._render_sync,
            template_name,
            context,
            output_path,
        )

    async def render_html_string(
        self,
        html_content: str,
        output_path: Path,
        css_string: str | None = None,
    ) -> Path:
        """Render a raw HTML string to PDF.

        Args:
            html_content: Complete HTML document string.
            output_path: Where to save the generated PDF.
            css_string: Optional CSS to apply to the document.

        Returns:
            The ``output_path`` on success.

        Raises:
            GenerationError: If WeasyPrint rendering fails.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(
            None,
            self._render_html_sync,
            html_content,
            output_path,
            css_string,
        )

    def _render_sync(
        self,
        template_name: str,
        context: dict[str, Any],
        output_path: Path,
    ) -> Path:
        """Synchronous rendering pipeline: Jinja2 -> HTML -> WeasyPrint -> PDF."""
        from jinja2 import Environment, FileSystemLoader
        from weasyprint import CSS, HTML

        template_dir = self._templates_dir / "resume" / template_name
        if not template_dir.exists():
            raise TemplateError(
                template_name,
                f"Template directory not found at {template_dir}",
            )

        html_file = template_dir / "template.html"
        if not html_file.exists():
            raise TemplateError(
                template_name,
                f"template.html not found in {template_dir}",
            )

        env = Environment(loader=FileSystemLoader(str(template_dir)))
        template = env.get_template("template.html")
        html_content = template.render(**context)

        # Load template CSS if present
        css_path = template_dir / "style.css"
        stylesheets: list[CSS] = []
        if css_path.exists():
            stylesheets.append(CSS(filename=str(css_path)))

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            HTML(string=html_content).write_pdf(
                str(output_path), stylesheets=stylesheets,
            )
        except Exception as exc:
            raise GenerationError(
                f"PDF rendering failed for template '{template_name}': {exc}",
            ) from exc

        logger.info(
            "pdf_rendered",
            template=template_name,
            output=str(output_path),
            size_bytes=output_path.stat().st_size,
        )
        return output_path

    def _render_html_sync(
        self,
        html_content: str,
        output_path: Path,
        css_string: str | None,
    ) -> Path:
        """Render raw HTML string to PDF."""
        from weasyprint import CSS, HTML

        stylesheets: list[CSS] = []
        if css_string:
            stylesheets.append(CSS(string=css_string))

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            HTML(string=html_content).write_pdf(
                str(output_path), stylesheets=stylesheets,
            )
        except Exception as exc:
            raise GenerationError(
                f"PDF rendering from HTML string failed: {exc}",
            ) from exc

        logger.info(
            "pdf_rendered_from_html",
            output=str(output_path),
            size_bytes=output_path.stat().st_size,
        )
        return output_path
