"""Integration tests for the Jobs API routes."""

import pytest

from app.models.job import Job

API_PREFIX = "/api/v1/jobs"


@pytest.fixture
def job_data(sample_job_data):
    """Provide sample_job_data with skills_required as a dict (matching schema)."""
    data = dict(sample_job_data)
    data["skills_required"] = {"python": True, "fastapi": True, "postgresql": True}
    return data


class TestSearchJobs:
    """Tests for POST /api/v1/jobs/search."""

    async def test_search_returns_empty_results(self, client):
        response = await client.post(
            f"{API_PREFIX}/search",
            json={"query": "python developer", "location": "Remote"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["has_next"] is False

    async def test_search_requires_query(self, client):
        response = await client.post(f"{API_PREFIX}/search", json={})

        assert response.status_code == 422

    async def test_search_rejects_empty_query(self, client):
        response = await client.post(f"{API_PREFIX}/search", json={"query": ""})

        assert response.status_code == 422


class TestListJobs:
    """Tests for GET /api/v1/jobs/."""

    async def test_list_empty(self, client):
        response = await client.get(f"{API_PREFIX}/")

        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0
        assert body["page"] == 1
        assert body["has_next"] is False

    async def test_list_with_pagination_params(self, client):
        response = await client.get(f"{API_PREFIX}/", params={"page": 2, "page_size": 5})

        assert response.status_code == 200
        body = response.json()
        assert body["page"] == 2
        assert body["page_size"] == 5

    async def test_list_returns_created_job(self, client, db_session, job_data):
        job = Job(**job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.get(f"{API_PREFIX}/")

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        assert body["items"][0]["title"] == "Senior Python Developer"
        assert body["items"][0]["company"] == "TechCorp Inc."

    async def test_list_filter_by_status(self, client, db_session, job_data):
        job = Job(**job_data)
        db_session.add(job)
        await db_session.commit()

        response = await client.get(f"{API_PREFIX}/", params={"status": "new"})
        assert response.status_code == 200
        assert response.json()["total"] == 1

        response = await client.get(f"{API_PREFIX}/", params={"status": "applied"})
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestGetJob:
    """Tests for GET /api/v1/jobs/{job_id}."""

    async def test_get_nonexistent_returns_404(self, client):
        response = await client.get(f"{API_PREFIX}/nonexistent-id")

        assert response.status_code == 404

    async def test_get_existing_job(self, client, db_session, job_data):
        job = Job(**job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.get(f"{API_PREFIX}/{job.id}")

        assert response.status_code == 200
        body = response.json()
        assert body["id"] == job.id
        assert body["title"] == "Senior Python Developer"
        assert body["platform"] == "linkedin"
        assert body["remote"] is True


class TestAnalyzeJob:
    """Tests for POST /api/v1/jobs/{job_id}/analyze."""

    async def test_analyze_nonexistent_returns_404(self, client):
        response = await client.post(f"{API_PREFIX}/nonexistent-id/analyze")

        assert response.status_code == 404

    async def test_analyze_existing_job(self, client, db_session, job_data):
        job = Job(**job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.post(f"{API_PREFIX}/{job.id}/analyze")

        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == job.id
        assert "match_score" in body
        assert "skill_match" in body
        assert "keyword_match" in body
        assert "missing_skills" in body
        assert "suggestions" in body


class TestDeleteJob:
    """Tests for DELETE /api/v1/jobs/{job_id}."""

    async def test_delete_nonexistent_returns_404(self, client):
        response = await client.delete(f"{API_PREFIX}/nonexistent-id")

        assert response.status_code == 404

    async def test_delete_existing_job(self, client, db_session, job_data):
        job = Job(**job_data)
        db_session.add(job)
        await db_session.commit()
        await db_session.refresh(job)

        response = await client.delete(f"{API_PREFIX}/{job.id}")
        assert response.status_code == 204

        # Verify job is gone
        response = await client.get(f"{API_PREFIX}/{job.id}")
        assert response.status_code == 404
