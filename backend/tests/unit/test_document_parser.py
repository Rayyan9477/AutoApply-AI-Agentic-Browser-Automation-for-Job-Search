"""Unit tests for app.core.documents.parser.DocumentParser."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.documents.parser import DocumentParser, ParsedResume
from app.core.exceptions import ParseError

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RESUME = """\
John Doe
john.doe@example.com
(555) 123-4567
linkedin.com/in/johndoe
github.com/johndoe

Summary
Experienced software engineer with 5 years of Python development.

Experience
Senior Software Engineer at Acme Corp (2020-2024)
Built scalable microservices handling 10M requests/day.

Education
Bachelor of Science in Computer Science, MIT, 2018

Skills
Python, JavaScript, Docker, Kubernetes, SQL
"""


@pytest.fixture()
def parser() -> DocumentParser:
    return DocumentParser()


# ---------------------------------------------------------------------------
# PDF parsing
# ---------------------------------------------------------------------------


class TestParsePDF:
    async def test_parse_pdf_extracts_text(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        pdf_file = tmp_path / "resume.pdf"
        pdf_file.touch()

        mock_page = MagicMock()
        mock_page.extract_text.return_value = SAMPLE_RESUME

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("app.core.documents.parser.DocumentParser._parse_pdf_sync", return_value=SAMPLE_RESUME):
            result = await parser.parse(pdf_file)

        assert isinstance(result, ParsedResume)
        assert result.file_format == "pdf"
        assert result.word_count > 0

    async def test_parse_nonexistent_file_raises_parse_error(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        missing = tmp_path / "missing.pdf"
        with pytest.raises(ParseError):
            await parser.parse(missing)


# ---------------------------------------------------------------------------
# DOCX parsing
# ---------------------------------------------------------------------------


class TestParseDocx:
    async def test_parse_docx_extracts_text(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        docx_file = tmp_path / "resume.docx"
        docx_file.touch()

        with patch("app.core.documents.parser.DocumentParser._parse_docx_sync", return_value=SAMPLE_RESUME):
            result = await parser.parse(docx_file)

        assert isinstance(result, ParsedResume)
        assert result.file_format == "docx"


# ---------------------------------------------------------------------------
# Unsupported format
# ---------------------------------------------------------------------------


class TestUnsupportedFormat:
    async def test_unsupported_extension_raises_parse_error(
        self, parser: DocumentParser, tmp_path: Path
    ) -> None:
        txt_file = tmp_path / "resume.txt"
        txt_file.touch()
        with pytest.raises(ParseError, match="Unsupported format"):
            await parser.parse(txt_file)


# ---------------------------------------------------------------------------
# Contact extraction
# ---------------------------------------------------------------------------


class TestContactExtraction:
    def test_extracts_email(self, parser: DocumentParser) -> None:
        info = parser._extract_contact_info("Contact me at john@example.com for details.")
        assert info["email"] == "john@example.com"

    def test_extracts_phone(self, parser: DocumentParser) -> None:
        info = parser._extract_contact_info("Phone: (555) 123-4567")
        assert "phone" in info

    def test_extracts_linkedin(self, parser: DocumentParser) -> None:
        info = parser._extract_contact_info("linkedin.com/in/johndoe")
        assert "linkedin" in info

    def test_extracts_github(self, parser: DocumentParser) -> None:
        info = parser._extract_contact_info("github.com/johndoe")
        assert "github" in info


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------


class TestSectionExtraction:
    def test_extracts_known_sections(self, parser: DocumentParser) -> None:
        sections = parser._extract_sections(SAMPLE_RESUME)
        assert "summary" in sections
        assert "experience" in sections
        assert "education" in sections
        assert "skills" in sections

    def test_section_content_is_nonempty(self, parser: DocumentParser) -> None:
        sections = parser._extract_sections(SAMPLE_RESUME)
        for name, content in sections.items():
            assert len(content.strip()) > 0, f"Section '{name}' is empty"

    def test_no_sections_returns_empty_dict(self, parser: DocumentParser) -> None:
        sections = parser._extract_sections("Just some random text\nwith no headings.")
        assert sections == {}

    def test_colon_after_header_is_stripped(self, parser: DocumentParser) -> None:
        text = "Skills:\nPython, Docker, SQL"
        sections = parser._extract_sections(text)
        assert "skills" in sections


# ---------------------------------------------------------------------------
# Skill extraction
# ---------------------------------------------------------------------------


class TestSkillExtraction:
    def test_extracts_comma_separated_skills(self, parser: DocumentParser) -> None:
        sections = {"skills": "Python, JavaScript, Docker, Kubernetes, SQL"}
        skills = parser._extract_skills_from_text("", sections)
        assert "Python" in skills
        assert "Docker" in skills

    def test_extracts_pipe_separated_skills(self, parser: DocumentParser) -> None:
        sections = {"skills": "Python | JavaScript | Docker"}
        skills = parser._extract_skills_from_text("", sections)
        assert "Python" in skills
        assert len(skills) == 3

    def test_falls_back_to_full_text(self, parser: DocumentParser) -> None:
        skills = parser._extract_skills_from_text("Python, Docker, SQL", {})
        assert "Python" in skills

    def test_deduplicates_skills(self, parser: DocumentParser) -> None:
        sections = {"skills": "Python, python, PYTHON"}
        skills = parser._extract_skills_from_text("", sections)
        python_variants = [s for s in skills if s.lower() == "python"]
        assert len(python_variants) == 1

    def test_skips_empty_lines(self, parser: DocumentParser) -> None:
        sections = {"skills": "\n\n\nPython\n\nDocker\n\n"}
        skills = parser._extract_skills_from_text("", sections)
        assert len(skills) >= 2


# ---------------------------------------------------------------------------
# _parse_pdf_sync and _parse_docx_sync edge cases
# ---------------------------------------------------------------------------


class TestParseSyncEdgeCases:
    def test_pdf_no_text_raises_parse_error(self, parser: DocumentParser, tmp_path: Path) -> None:
        pdf_file = tmp_path / "empty.pdf"
        pdf_file.touch()

        mock_page = MagicMock()
        mock_page.extract_text.return_value = ""
        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]

        with patch("PyPDF2.PdfReader", return_value=mock_reader):
            with pytest.raises(ParseError, match="No text content"):
                parser._parse_pdf_sync(pdf_file)

    def test_docx_no_text_raises_parse_error(self, parser: DocumentParser, tmp_path: Path) -> None:
        docx_file = tmp_path / "empty.docx"
        docx_file.touch()

        mock_para = MagicMock()
        mock_para.text = ""
        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]

        with patch("docx.Document", return_value=mock_doc):
            with pytest.raises(ParseError, match="No text content"):
                parser._parse_docx_sync(docx_file)

    async def test_parse_catches_generic_exception(self, parser: DocumentParser, tmp_path: Path) -> None:
        pdf_file = tmp_path / "bad.pdf"
        pdf_file.touch()

        with patch.object(parser, "_parse_pdf_sync", side_effect=RuntimeError("boom")):
            with pytest.raises(ParseError, match="boom"):
                await parser.parse(pdf_file)
