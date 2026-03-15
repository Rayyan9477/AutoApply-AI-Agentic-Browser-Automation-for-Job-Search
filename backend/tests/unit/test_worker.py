"""Unit tests for the application worker (app.workers.application_worker).

All external dependencies (DB, Redis, platform registry, WebSocket manager)
are mocked so these tests run without infrastructure.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from app.config.constants import ApplicationStatus
from app.workers.application_worker import process_application

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_payload(
    job_id: str = "job-1",
    application_id: str = "app-1",
    platform: str = "linkedin",
    resume_id: str = "",
) -> dict:
    return {
        "job_id": job_id,
        "application_id": application_id,
        "platform": platform,
        "resume_id": resume_id,
    }


def _make_mock_job():
    """Create a mock Job model instance."""
    job = MagicMock()
    job.id = "job-1"
    job.platform = "linkedin"
    job.platform_job_id = "ext-123"
    job.title = "Senior Python Dev"
    job.company = "TestCorp"
    job.location = "Remote"
    job.url = "https://example.com/job/123"
    job.description = "We need a Python developer"
    job.job_type = "full-time"
    job.remote = True
    job.skills_required = {"skills": ["python"]}
    return job


def _make_mock_session(job=None):
    """Create an async context manager mock for async_session_factory."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = job
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()
    return mock_session


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestProcessApplicationHappyPath:
    async def test_process_application_happy_path(self):
        """Worker should broadcast progress stages and complete successfully
        when the platform is registered and job is found."""
        payload = _make_payload()
        mock_job = _make_mock_job()

        mock_platform = AsyncMock()
        mock_platform.apply = AsyncMock(return_value=True)

        with (
            patch(
                "app.workers.application_worker.ws_manager",
            ) as mock_ws,
            patch(
                "app.workers.application_worker.platform_registry",
            ) as mock_registry,
            patch(
                "app.workers.application_worker.get_settings",
            ) as mock_settings,
            patch(
                "app.workers.application_worker.async_session_factory",
            ) as mock_sf,
            patch(
                "app.workers.application_worker._update_application_status",
                new_callable=AsyncMock,
            ),
        ):
            mock_ws.broadcast = AsyncMock()
            mock_registry.has.return_value = True
            mock_registry.create.return_value = mock_platform
            mock_settings.return_value = MagicMock(min_ats_score=0.75)

            mock_session = _make_mock_session(mock_job)
            mock_sf.return_value.__aenter__ = AsyncMock(
                return_value=mock_session,
            )
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_application(payload)

        # Verify progress broadcasts happened in order
        broadcast_calls = mock_ws.broadcast.call_args_list
        statuses = [call.args[0]["status"] for call in broadcast_calls]

        assert statuses[0] == ApplicationStatus.APPLYING
        assert ApplicationStatus.APPLIED in statuses
        assert "loading_job" in statuses
        assert "generating_resume" in statuses
        assert "scoring_ats" in statuses
        assert "submitting" in statuses

    async def test_process_application_sets_application_id(self):
        """Every broadcast should include the application_id."""
        payload = _make_payload(application_id="app-42")
        mock_job = _make_mock_job()

        mock_platform = AsyncMock()
        mock_platform.apply = AsyncMock(return_value=True)

        with (
            patch(
                "app.workers.application_worker.ws_manager",
            ) as mock_ws,
            patch(
                "app.workers.application_worker.platform_registry",
            ) as mock_registry,
            patch(
                "app.workers.application_worker.get_settings",
            ) as mock_settings,
            patch(
                "app.workers.application_worker.async_session_factory",
            ) as mock_sf,
            patch(
                "app.workers.application_worker._update_application_status",
                new_callable=AsyncMock,
            ),
        ):
            mock_ws.broadcast = AsyncMock()
            mock_registry.has.return_value = True
            mock_registry.create.return_value = mock_platform
            mock_settings.return_value = MagicMock(min_ats_score=0.75)

            mock_session = _make_mock_session(mock_job)
            mock_sf.return_value.__aenter__ = AsyncMock(
                return_value=mock_session,
            )
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_application(payload)

        for call in mock_ws.broadcast.call_args_list:
            assert call.args[0]["application_id"] == "app-42"


class TestProcessApplicationErrors:
    async def test_worker_handles_unknown_platform(self):
        """When the platform is not registered, worker should broadcast
        a FAILED status and return gracefully."""
        payload = _make_payload(platform="unknown_platform")

        with (
            patch(
                "app.workers.application_worker.ws_manager",
            ) as mock_ws,
            patch(
                "app.workers.application_worker.platform_registry",
            ) as mock_registry,
            patch(
                "app.workers.application_worker._update_application_status",
                new_callable=AsyncMock,
            ),
        ):
            mock_ws.broadcast = AsyncMock()
            mock_registry.has.return_value = False

            await process_application(payload)

        last_call = mock_ws.broadcast.call_args_list[-1]
        msg = last_call.args[0]
        assert msg["status"] == ApplicationStatus.FAILED
        assert "unknown_platform" in msg.get("detail", "").lower()

    async def test_worker_handles_empty_payload(self):
        """Worker should handle an empty payload without crashing."""
        payload: dict = {}

        with (
            patch(
                "app.workers.application_worker.ws_manager",
            ) as mock_ws,
            patch(
                "app.workers.application_worker.platform_registry",
            ) as mock_registry,
            patch(
                "app.workers.application_worker._update_application_status",
                new_callable=AsyncMock,
            ),
        ):
            mock_ws.broadcast = AsyncMock()
            mock_registry.has.return_value = False

            # Should not raise
            await process_application(payload)

        # Should have broadcast at least a FAILED status
        assert mock_ws.broadcast.call_count >= 1

    async def test_worker_handles_autoapply_error(self):
        """When an AutoApplyError is raised, worker should broadcast FAILED
        with error detail."""
        from app.core.exceptions import AutoApplyError

        payload = _make_payload()

        with (
            patch(
                "app.workers.application_worker.ws_manager",
            ) as mock_ws,
            patch(
                "app.workers.application_worker.platform_registry",
            ) as mock_registry,
            patch(
                "app.workers.application_worker.get_settings",
                side_effect=AutoApplyError(
                    "ATS scoring failed", code="ATS_ERROR",
                ),
            ),
            patch(
                "app.workers.application_worker.async_session_factory",
            ) as mock_sf,
            patch(
                "app.workers.application_worker._update_application_status",
                new_callable=AsyncMock,
            ),
        ):
            mock_ws.broadcast = AsyncMock()
            mock_registry.has.return_value = True

            mock_session = _make_mock_session(_make_mock_job())
            mock_sf.return_value.__aenter__ = AsyncMock(
                return_value=mock_session,
            )
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_application(payload)

        last_call = mock_ws.broadcast.call_args_list[-1]
        msg = last_call.args[0]
        assert msg["status"] == ApplicationStatus.FAILED
        assert "ATS scoring failed" in msg.get("detail", "")

    async def test_worker_handles_unexpected_exception(self):
        """When an unexpected exception is raised, worker should broadcast
        FAILED with generic message."""
        payload = _make_payload()

        with (
            patch(
                "app.workers.application_worker.ws_manager",
            ) as mock_ws,
            patch(
                "app.workers.application_worker.platform_registry",
            ) as mock_registry,
            patch(
                "app.workers.application_worker.get_settings",
                side_effect=RuntimeError("unexpected boom"),
            ),
            patch(
                "app.workers.application_worker.async_session_factory",
            ) as mock_sf,
            patch(
                "app.workers.application_worker._update_application_status",
                new_callable=AsyncMock,
            ),
        ):
            mock_ws.broadcast = AsyncMock()
            mock_registry.has.return_value = True

            mock_session = _make_mock_session(_make_mock_job())
            mock_sf.return_value.__aenter__ = AsyncMock(
                return_value=mock_session,
            )
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_application(payload)

        last_call = mock_ws.broadcast.call_args_list[-1]
        msg = last_call.args[0]
        assert msg["status"] == ApplicationStatus.FAILED
        assert "unexpected" in msg.get("detail", "").lower()

    async def test_worker_handles_job_not_found(self):
        """When the job is not found in DB, worker should broadcast FAILED."""
        payload = _make_payload()

        with (
            patch(
                "app.workers.application_worker.ws_manager",
            ) as mock_ws,
            patch(
                "app.workers.application_worker.platform_registry",
            ) as mock_registry,
            patch(
                "app.workers.application_worker.get_settings",
            ) as mock_settings,
            patch(
                "app.workers.application_worker.async_session_factory",
            ) as mock_sf,
            patch(
                "app.workers.application_worker._update_application_status",
                new_callable=AsyncMock,
            ),
        ):
            mock_ws.broadcast = AsyncMock()
            mock_registry.has.return_value = True
            mock_settings.return_value = MagicMock(min_ats_score=0.75)

            # Return None for job lookup
            mock_session = _make_mock_session(None)
            mock_sf.return_value.__aenter__ = AsyncMock(
                return_value=mock_session,
            )
            mock_sf.return_value.__aexit__ = AsyncMock(return_value=False)

            await process_application(payload)

        last_call = mock_ws.broadcast.call_args_list[-1]
        msg = last_call.args[0]
        assert msg["status"] == ApplicationStatus.FAILED
        assert "not found" in msg.get("detail", "").lower()


class TestBroadcastProgress:
    async def test_broadcast_includes_detail_when_provided(self):
        """_broadcast_progress should include detail in the message."""
        from app.workers.application_worker import _broadcast_progress

        with patch(
            "app.workers.application_worker.ws_manager",
        ) as mock_ws:
            mock_ws.broadcast = AsyncMock()
            await _broadcast_progress("app-1", "applying", detail="Step 1")

        msg = mock_ws.broadcast.call_args.args[0]
        assert msg["detail"] == "Step 1"

    async def test_broadcast_omits_detail_when_empty(self):
        """_broadcast_progress should not include detail key when empty."""
        from app.workers.application_worker import _broadcast_progress

        with patch(
            "app.workers.application_worker.ws_manager",
        ) as mock_ws:
            mock_ws.broadcast = AsyncMock()
            await _broadcast_progress("app-1", "applying")

        msg = mock_ws.broadcast.call_args.args[0]
        assert "detail" not in msg


class TestRunWorker:
    async def test_run_worker_exits_when_no_redis(self):
        """run_worker should return immediately if Redis is unavailable."""
        from app.workers.application_worker import run_worker

        with patch(
            "app.workers.application_worker.get_redis", return_value=None,
        ):
            await run_worker()  # should not block or raise
