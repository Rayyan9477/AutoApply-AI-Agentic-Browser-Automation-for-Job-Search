"""Integration tests for the /api/v1/resumes endpoints."""

from __future__ import annotations

from unittest.mock import patch

from app.models.job import Job
from app.models.resume import Resume


async def _create_base_resume(db_session, name="Test Resume"):
    r = Resume(name=name, type="base", template_id="modern")
    db_session.add(r)
    await db_session.commit()
    await db_session.refresh(r)
    return r


async def _create_job(db_session):
    job = Job(
        platform="linkedin",
        platform_job_id="api-test-job",
        title="Python Developer",
        company="TestCorp",
        location="Remote",
        url="https://example.com/job/1",
        description="Python developer needed",
        job_type="full-time",
        remote=True,
        match_score=0.9,
        skills_required=["python"],
        status="new",
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


class TestListResumesAPI:
    async def test_list_resumes_returns_200(self, client):
        resp = await client.get("/api/v1/resumes/")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data


class TestUploadResumeAPI:
    async def test_upload_resume_returns_201(self, client, db_session, tmp_path):
        import app.services.resume as resume_service

        with patch.object(resume_service, "UPLOAD_DIR", tmp_path):
            resp = await client.post(
                "/api/v1/resumes/upload",
                files={"file": ("resume.pdf", b"fake pdf content", "application/pdf")},
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["file_format"] == "pdf"
        assert data["name"] == "resume.pdf"


class TestGenerateResumeAPI:
    async def test_generate_resume_returns_201(self, client, db_session):
        resume = await _create_base_resume(db_session)
        job = await _create_job(db_session)

        resp = await client.post(
            "/api/v1/resumes/generate",
            json={
                "base_resume_id": resume.id,
                "job_id": job.id,
                "template_id": "classic",
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["type"] == "tailored"


class TestScoreResumeAPI:
    async def test_score_resume_returns_200(self, client, db_session):
        resume = await _create_base_resume(db_session)
        job = await _create_job(db_session)

        resp = await client.post(
            f"/api/v1/resumes/{resume.id}/score",
            json={"job_id": job.id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_score" in data


class TestOptimizeResumeAPI:
    async def test_optimize_returns_200(self, client, db_session):
        resume = await _create_base_resume(db_session)
        resp = await client.post(f"/api/v1/resumes/{resume.id}/optimize")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == resume.id
