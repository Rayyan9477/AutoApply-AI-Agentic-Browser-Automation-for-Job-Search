"""Integration tests for exception handler in app.main."""

from __future__ import annotations

from unittest.mock import patch

from app.core.exceptions import (
    AuthenticationError,
    IntegrityError,
    LLMRateLimitError,
)


class TestExceptionHandlerMapping:
    async def test_record_not_found_returns_404(self, client):
        """RecordNotFoundError should map to 404."""
        resp = await client.get("/api/v1/resumes/nonexistent-id/score")
        # score endpoint requires POST, but trying to get a missing resume
        # Use a known endpoint that triggers RecordNotFoundError
        resp = await client.post(
            "/api/v1/resumes/nonexistent-id/score",
            json={"job_id": "fake-job"},
        )
        assert resp.status_code == 404
        data = resp.json()
        assert data["code"] == "RECORD_NOT_FOUND"

    async def test_record_not_found_optimize(self, client):
        """Optimize a nonexistent resume should return 404."""
        resp = await client.post("/api/v1/resumes/nonexistent-id/optimize")
        assert resp.status_code == 404

    async def test_auth_error_returns_401(self, client):
        """AuthenticationError should map to 401."""
        with patch(
            "app.services.resume.list_resumes",
            side_effect=AuthenticationError("linkedin"),
        ):
            resp = await client.get("/api/v1/resumes/")
        assert resp.status_code == 401

    async def test_rate_limit_returns_429(self, client):
        """LLMRateLimitError should map to 429."""
        with patch(
            "app.services.resume.list_resumes",
            side_effect=LLMRateLimitError("openai", retry_after=30),
        ):
            resp = await client.get("/api/v1/resumes/")
        assert resp.status_code == 429

    async def test_integrity_error_returns_409(self, client):
        """IntegrityError should map to 409."""
        with patch(
            "app.services.resume.list_resumes",
            side_effect=IntegrityError("duplicate entry"),
        ):
            resp = await client.get("/api/v1/resumes/")
        assert resp.status_code == 409
