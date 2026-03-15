"""Unit tests for the resume service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.exceptions import RecordNotFoundError
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.resume import ResumeGenerateRequest, ResumeScoreRequest
from app.services import resume as resume_service


async def _create_base_resume(db_session, name="Base Resume"):
    """Helper to create a base resume record."""
    r = Resume(name=name, type="base", template_id="modern")
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    return r


async def _create_job(db_session, sample_job_data, suffix="0"):
    data = {**sample_job_data, "platform_job_id": f"job-{suffix}"}
    job = Job(**data)
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


class TestListResumes:
    async def test_list_resumes_empty(self, db_session):
        result = await resume_service.list_resumes(db_session)
        assert result.items == []
        assert result.total == 0


class TestGenerateTailoredResume:
    async def test_generate_tailored_resume(self, db_session, sample_job_data):
        base = await _create_base_resume(db_session)
        job = await _create_job(db_session, sample_job_data)

        request = ResumeGenerateRequest(
            base_resume_id=base.id,
            job_id=job.id,
            template_id="classic",
        )
        result = await resume_service.generate_tailored_resume(db_session, request)

        assert result.type == "tailored"
        assert result.base_resume_id == base.id
        assert result.job_id == job.id
        assert result.template_id == "classic"
        assert "Tailored" in result.name


class TestScoreResume:
    async def test_score_resume_empty_text(self, db_session, sample_job_data):
        """Resume with no content_text returns zero scores."""
        base = await _create_base_resume(db_session)
        job = await _create_job(db_session, sample_job_data)

        request = ResumeScoreRequest(job_id=job.id)
        result = await resume_service.score_resume(db_session, base.id, request)

        assert result.resume_id == base.id
        assert result.job_id == job.id
        assert result.overall_score == 0.0
        assert result.skill_score == 0.0
        assert len(result.missing_skills) > 0
        assert len(result.suggestions) > 0

    async def test_score_resume_with_content(self, db_session, sample_job_data):
        """Resume with content_text returns real scores."""
        r = Resume(
            name="Parsed Resume",
            type="base",
            template_id="modern",
            content_text="Experienced Python developer with FastAPI and PostgreSQL skills",
        )
        db_session.add(r)
        await db_session.commit()
        await db_session.refresh(r)

        job = await _create_job(db_session, sample_job_data)

        request = ResumeScoreRequest(job_id=job.id)
        result = await resume_service.score_resume(db_session, r.id, request)

        assert result.resume_id == r.id
        assert result.job_id == job.id
        # Should have a non-zero score since resume text mentions job skills
        assert 0.0 <= result.overall_score <= 1.0
        assert 0.0 <= result.skill_score <= 1.0
        assert 0.0 <= result.keyword_score <= 1.0


class TestUploadResume:
    async def test_upload_resume_creates_record(self, db_session, tmp_path):
        mock_file = MagicMock()
        mock_file.filename = "my_resume.pdf"
        mock_file.read = AsyncMock(return_value=b"fake pdf content here with enough words to count")

        with patch.object(resume_service, "UPLOAD_DIR", tmp_path):
            result = await resume_service.upload_resume(db_session, mock_file)

        assert result.name == "my_resume.pdf"
        assert result.file_format == "pdf"
        assert result.word_count > 0
        assert result.id is not None

    async def test_upload_docx_sets_correct_format(self, db_session, tmp_path):
        mock_file = MagicMock()
        mock_file.filename = "resume.docx"
        mock_file.read = AsyncMock(return_value=b"fake docx content")

        with patch.object(resume_service, "UPLOAD_DIR", tmp_path):
            result = await resume_service.upload_resume(db_session, mock_file)

        assert result.file_format == "docx"

    async def test_upload_with_no_filename(self, db_session, tmp_path):
        mock_file = MagicMock()
        mock_file.filename = None
        mock_file.read = AsyncMock(return_value=b"content")

        with patch.object(resume_service, "UPLOAD_DIR", tmp_path):
            result = await resume_service.upload_resume(db_session, mock_file)

        assert result.name == "Untitled Resume"
        assert result.file_format == "pdf"


class TestGetResumeNotFound:
    async def test_get_resume_not_found(self, db_session):
        with pytest.raises(RecordNotFoundError):
            await resume_service.get_resume(db_session, "nonexistent_id")
