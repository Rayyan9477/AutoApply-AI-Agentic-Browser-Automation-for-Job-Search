"""End-to-end tests exercising the full API pipeline.

These tests use httpx.AsyncClient against the real FastAPI app with an
in-memory SQLite database. Redis and external services are not required.
"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_job_in_db(db: AsyncSession, idx: int = 1) -> Job:
    """Insert a Job row directly and return the model instance."""
    job = Job(
        platform="linkedin",
        platform_job_id=f"e2e-job-{idx}",
        title=f"Python Developer {idx}",
        company=f"TestCorp {idx}",
        location="Remote",
        url=f"https://example.com/jobs/{idx}",
        description=f"Job description for position {idx}.",
        status="new",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


# ---------------------------------------------------------------------------
# 1. Full search -> application -> approve -> status pipeline
# ---------------------------------------------------------------------------


class TestFullJobSearchToApplicationPipeline:
    async def test_full_job_search_to_application_pipeline(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Step 1: POST /api/v1/jobs/search -- placeholder returns empty
        resp = await client.post(
            "/api/v1/jobs/search",
            json={"query": "python developer", "location": "remote"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] == 0

        # Step 2: GET /api/v1/jobs/ -- verify response structure
        resp = await client.get("/api/v1/jobs/")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "page" in body
        assert "page_size" in body
        assert "has_next" in body

        # Step 3: Create a Job directly in DB
        job = await _create_job_in_db(db_session, idx=100)
        job_id = job.id

        # Step 4: POST /api/v1/jobs/{job_id}/analyze
        resp = await client.post(f"/api/v1/jobs/{job_id}/analyze")
        assert resp.status_code == 200
        analysis = resp.json()
        assert analysis["job_id"] == job_id
        assert "match_score" in analysis
        assert "skill_match" in analysis
        assert "missing_skills" in analysis

        # Step 5: POST /api/v1/applications/ with the job_id
        resp = await client.post(
            "/api/v1/applications/",
            json={"job_id": job_id},
        )
        assert resp.status_code == 201
        app_data = resp.json()
        app_id = app_data["id"]
        assert app_data["job_id"] == job_id
        assert app_data["status"] == "queued"

        # Step 6: GET /api/v1/applications/{app_id}
        resp = await client.get(f"/api/v1/applications/{app_id}")
        assert resp.status_code == 200
        assert resp.json()["status"] == "queued"

        # Step 7: PUT /api/v1/applications/{app_id}/approve
        resp = await client.put(f"/api/v1/applications/{app_id}/approve")
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        # Step 8: PUT /api/v1/applications/{app_id}/status  ->  applied
        resp = await client.put(
            f"/api/v1/applications/{app_id}/status",
            json={"status": "applied"},
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["status"] == "applied"
        assert updated["applied_at"] is not None


# ---------------------------------------------------------------------------
# 2. Batch application workflow
# ---------------------------------------------------------------------------


class TestBatchApplicationWorkflow:
    async def test_batch_application_workflow(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Create 3 jobs in DB
        jobs = []
        for i in range(1, 4):
            j = await _create_job_in_db(db_session, idx=200 + i)
            jobs.append(j)

        job_ids = [j.id for j in jobs]

        # POST /api/v1/applications/batch
        resp = await client.post(
            "/api/v1/applications/batch",
            json={"job_ids": job_ids},
        )
        assert resp.status_code == 201
        batch = resp.json()
        assert len(batch) == 3

        # GET /api/v1/applications/ -- verify 3 exist
        resp = await client.get("/api/v1/applications/")
        assert resp.status_code == 200
        listing = resp.json()
        assert listing["total"] >= 3

        # All are in "queued" status
        for app_resp in batch:
            assert app_resp["status"] == "queued"


# ---------------------------------------------------------------------------
# 3. Dashboard reflects application state
# ---------------------------------------------------------------------------


class TestDashboardReflectsApplicationState:
    async def test_dashboard_reflects_application_state(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        # Create a job and two applications with different statuses
        job = await _create_job_in_db(db_session, idx=300)

        resp1 = await client.post(
            "/api/v1/applications/",
            json={"job_id": job.id},
        )
        assert resp1.status_code == 201
        app1_id = resp1.json()["id"]

        resp2 = await client.post(
            "/api/v1/applications/",
            json={"job_id": job.id},
        )
        assert resp2.status_code == 201

        # Move app1 to "applied"
        await client.put(
            f"/api/v1/applications/{app1_id}/status",
            json={"status": "applied"},
        )

        # GET /api/v1/analytics/dashboard
        resp = await client.get("/api/v1/analytics/dashboard")
        assert resp.status_code == 200
        stats = resp.json()
        assert stats["total_jobs_found"] >= 1
        assert stats["total_applications"] >= 2
        assert stats["applications_applied"] >= 1

        # GET /api/v1/analytics/funnel
        resp = await client.get("/api/v1/analytics/funnel")
        assert resp.status_code == 200
        funnel = resp.json()
        assert isinstance(funnel, list)
        assert len(funnel) > 0
        # Each entry has stage + count
        for entry in funnel:
            assert "stage" in entry
            assert "count" in entry


# ---------------------------------------------------------------------------
# 4. Settings persist across requests
# ---------------------------------------------------------------------------


class TestSettingsPersistAcrossRequests:
    async def test_settings_persist_across_requests(self, client: AsyncClient):
        # GET defaults
        resp = await client.get("/api/v1/settings/")
        assert resp.status_code == 200
        defaults = resp.json()
        assert "apply_mode" in defaults
        assert "min_ats_score" in defaults

        # PUT updated settings
        resp = await client.put(
            "/api/v1/settings/",
            json={"apply_mode": "autonomous", "min_ats_score": 0.85},
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["apply_mode"] == "autonomous"
        assert updated["min_ats_score"] == 0.85

        # GET again -- verify persisted
        resp = await client.get("/api/v1/settings/")
        assert resp.status_code == 200
        persisted = resp.json()
        assert persisted["apply_mode"] == "autonomous"
        assert persisted["min_ats_score"] == 0.85

        # Restore defaults so other tests that rely on in-memory settings
        # state are not affected (the settings route uses a module-level global).
        await client.put(
            "/api/v1/settings/",
            json={"apply_mode": defaults["apply_mode"],
                  "min_ats_score": defaults["min_ats_score"]},
        )


# ---------------------------------------------------------------------------
# 5. Health endpoint
# ---------------------------------------------------------------------------


class TestHealthEndpoint:
    async def test_health_endpoint_returns_ok(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body
