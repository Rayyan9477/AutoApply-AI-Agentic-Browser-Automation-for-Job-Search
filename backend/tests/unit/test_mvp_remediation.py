"""Regression tests for the MVP remediation pass (see docs/CODE_REVIEW_FINDINGS.md).

Group 2 — contained backend fixes: M1 WS send-lock, M2/M3 anomaly dedup+window, M4 cover-letter
paragraphs, M7 cached spaCy, L1 review transient-retry, L2 resume autoescape, L5 register race.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from app.core.exceptions import LLMRateLimitError
from app.core.harness import record
from app.core.harness.anomaly import detect_anomalies
from app.models.application import Application
from app.models.enums import ApplicationStatus, ApplyMode
from app.models.harness import SystemIssue
from app.models.job import Job
from app.models.user import User
from app.workers import tasks
from tests.conftest import TEST_USER_ID

_REPO_ROOT = Path(__file__).resolve().parents[3]


# --- M1: WebSocket subscriber writes serialize through the per-socket lock ---------------


class _FakeWS:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.busy = False
        self.violation = False

    async def accept(self) -> None:
        pass

    async def send_text(self, text: str) -> None:
        if self.busy:  # a concurrent unlocked sender would see this
            self.violation = True
        self.busy = True
        await asyncio.sleep(0)  # yield so an unlocked concurrent sender could interleave
        self.busy = False
        self.sent.append(text)


class TestWebSocketSendRaw:
    async def test_send_raw_serializes_with_send_to(self) -> None:
        from app.api.websocket.events import ConnectionManager

        mgr = ConnectionManager()
        ws = _FakeWS()
        await mgr.connect(ws, "u1")  # type: ignore[arg-type]

        await asyncio.gather(
            mgr.send_raw(ws, "raw1"),  # type: ignore[arg-type]
            mgr.send_to(ws, {"n": 1}),  # type: ignore[arg-type]
            mgr.send_raw(ws, "raw2"),  # type: ignore[arg-type]
        )

        assert ws.violation is False  # the lock prevented interleaved send_text
        assert len(ws.sent) == 3


# --- M2 / M3: anomaly detector windows the rate and dedups the open issue -----------------


async def _seed_apps(db, *, total: int, failed: int, created_at: datetime | None = None) -> None:
    db.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
    for i in range(total):
        job = Job(
            user_id=TEST_USER_ID, platform="linkedin", platform_job_id=f"j{i}",
            title="t", company="c", url="https://x",
        )
        db.add(job)
        await db.flush()
        status = ApplicationStatus.FAILED if i < failed else ApplicationStatus.APPLIED
        app = Application(
            user_id=TEST_USER_ID, job_id=job.id, status=status, apply_mode=ApplyMode.AUTONOMOUS
        )
        if created_at is not None:
            app.created_at = created_at
        db.add(app)
    await db.commit()


class TestAnomalyWindowAndDedup:
    async def test_old_failures_outside_window_do_not_trip(self, db_session) -> None:
        old = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=8)
        await _seed_apps(db_session, total=6, failed=6, created_at=old)
        issues = await detect_anomalies(db_session)
        assert all(i.category != "apply_failure_rate" for i in issues)

    async def test_recent_failures_trip_once_without_duplicates(self, db_session) -> None:
        await _seed_apps(db_session, total=6, failed=4)  # created_at defaults to ~now
        first = await detect_anomalies(db_session)
        assert any(i.category == "apply_failure_rate" for i in first)

        # A second tick for the same ongoing condition must refresh, not insert a duplicate.
        await detect_anomalies(db_session)
        rows = (
            await db_session.execute(
                select(SystemIssue).where(SystemIssue.category == "apply_failure_rate")
            )
        ).scalars().all()
        assert len(rows) == 1


# --- M4: cover-letter PDF wraps paragraphs so they don't collapse -------------------------


class TestCoverLetterParagraphs:
    async def test_paragraphs_wrapped_in_p_tags(self, tmp_path) -> None:
        from app.core.documents.generator import DocumentGenerator
        from app.core.llm.prompts.cover_letter import CoverLetterTemplate

        gen = DocumentGenerator(llm_client=None, templates_dir=_REPO_ROOT / "templates")
        captured: dict[str, str] = {}

        async def _fake_render(html: str, out: Path, css: str | None = None) -> Path:
            captured["html"] = html
            return out

        gen._pdf.render_html_string = _fake_render  # type: ignore[assignment]
        content = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        await gen._render_cover_letter_pdf(
            content, CoverLetterTemplate.STANDARD, tmp_path / "cl.pdf"
        )
        assert captured["html"].count("<p>") >= 3


# --- M7: spaCy model is loaded once and cached -------------------------------------------


class TestNlpCache:
    def test_get_nlp_loads_once(self) -> None:
        from app.core.ats.nlp import get_nlp

        get_nlp.cache_clear()
        sentinel = object()
        with patch("spacy.load", return_value=sentinel) as mock_load:
            a = get_nlp()
            b = get_nlp()
        assert a is b is sentinel
        assert mock_load.call_count == 1
        get_nlp.cache_clear()


# --- L1: review job retries on a transient provider error --------------------------------


class _SessionCM:
    def __init__(self, db):
        self._db = db

    async def __aenter__(self):
        return self._db

    async def __aexit__(self, *exc):
        return False


class TestReviewTransientRetry:
    async def _trajectory(self, db):
        db.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db.commit()
        return await record.record_trajectory(
            db, user_id=TEST_USER_ID, application_id="app-1", platform="linkedin",
            agent_self_report="done", status="completed",
        )

    async def test_transient_error_propagates_for_retry(self, db_session) -> None:
        traj = await self._trajectory(db_session)
        with (
            patch.object(tasks, "async_session_factory", lambda: _SessionCM(db_session)),
            patch.object(tasks, "build_llm_client_for_user", AsyncMock(return_value=AsyncMock())),
            patch.object(tasks, "review_run", AsyncMock(side_effect=LLMRateLimitError(provider="x"))),
        ):
            with pytest.raises(LLMRateLimitError):
                await tasks.review_application_run({}, traj.id)

    async def test_permanent_error_is_swallowed(self, db_session) -> None:
        traj = await self._trajectory(db_session)
        with (
            patch.object(tasks, "async_session_factory", lambda: _SessionCM(db_session)),
            patch.object(tasks, "build_llm_client_for_user", AsyncMock(return_value=AsyncMock())),
            patch.object(tasks, "review_run", AsyncMock(side_effect=ValueError("bad data"))),
        ):
            # Non-transient errors are logged and swallowed (no infinite retry).
            await tasks.review_application_run({}, traj.id)


# --- L2: resume PDF renderer escapes HTML metacharacters ----------------------------------


class TestResumeAutoescape:
    def test_fields_are_html_escaped(self, tmp_path) -> None:
        from app.core.documents.pdf_renderer import PDFRenderer

        renderer = PDFRenderer(templates_dir=_REPO_ROOT / "templates")
        captured: dict[str, str] = {}

        # Intercept WeasyPrint (imported inside _render_sync) so we assert on the HTML string only.
        class _FakeHTML:
            def __init__(self, string: str) -> None:
                captured["html"] = string

            def write_pdf(self, path, stylesheets=None) -> None:
                Path(path).write_bytes(b"%PDF-1.4")

        with patch("weasyprint.HTML", _FakeHTML), patch("weasyprint.CSS"):
            renderer._render_sync(
                "modern",
                {"name": "A<b>C", "summary": "latency <5ms & up"},
                tmp_path / "r.pdf",
            )
        assert "&lt;5ms" in captured["html"] and "&amp;" in captured["html"]
        assert "<5ms" not in captured["html"]


# --- L5: register maps a race unique-violation to a clean 409 -----------------------------


class TestRegisterRace:
    async def test_commit_integrity_error_becomes_app_integrity_error(self) -> None:
        from sqlalchemy.exc import IntegrityError as DBIntegrityError

        from app.api.v1 import auth
        from app.core.exceptions import IntegrityError as AppIntegrityError
        from app.schemas.auth import RegisterRequest

        precheck = MagicMock()
        precheck.scalar_one_or_none.return_value = None  # the race: pre-check misses
        db = MagicMock()
        db.execute = AsyncMock(return_value=precheck)
        db.add = MagicMock()
        db.commit = AsyncMock(side_effect=DBIntegrityError("INSERT", {}, Exception("unique")))
        db.rollback = AsyncMock()

        with pytest.raises(AppIntegrityError):
            await auth.register(
                RegisterRequest(email="x@y.com", password="password123", full_name="X"), db
            )
        db.rollback.assert_awaited()


# --- H3: job-search dedup preserves distinct listings (no autoflush collapse) --------------


class _FakePlatform:
    def __init__(self, listings):
        self._listings = listings

    async def search(self, **kwargs):
        return self._listings


class TestJobSearchDedup:
    async def test_empty_ids_do_not_collapse_distinct_jobs(self, db_session) -> None:
        from app.core.automation.platforms.base import JobListing
        from app.schemas.job import JobSearchRequest
        from app.services.job_search import search_jobs

        db_session.add(User(id=TEST_USER_ID, email="u@x.com", hashed_password="x"))
        await db_session.commit()

        # All ids blank (the browser agent returned no id) but distinct URLs — must stay distinct.
        listings = [
            JobListing(
                platform="linkedin", platform_job_id="", title=f"Job {i}",
                company="C", url=f"https://x/{i}",
            )
            for i in range(3)
        ]
        reg = MagicMock()
        reg.list_platforms.return_value = ["linkedin"]
        reg.has.return_value = True
        reg.create.return_value = _FakePlatform(listings)

        with patch("app.services.job_search.platform_registry", reg):
            resp = await search_jobs(
                db_session, JobSearchRequest(query="python", limit=10), TEST_USER_ID
            )

        assert resp.total == 3
        assert {i.title for i in resp.items} == {"Job 0", "Job 1", "Job 2"}


# --- L6: identical skill content is not re-inserted --------------------------------------


class TestSkillContentDedup:
    async def test_duplicate_content_returns_existing(self, db_session) -> None:
        from sqlalchemy import select as _select

        from app.core.harness.skills import record_skill
        from app.models.harness import DomainSkill

        first = await record_skill(db_session, "linkedin", "Easy Apply at .jobs-apply-button")
        again = await record_skill(db_session, "linkedin", "Easy Apply at .jobs-apply-button")
        other = await record_skill(db_session, "linkedin", "Pagination reloads the page")

        assert again is not None and again.id == first.id  # deduped
        assert other is not None and other.id != first.id  # distinct content still inserted
        rows = (
            await db_session.execute(_select(DomainSkill).where(DomainSkill.domain == "linkedin"))
        ).scalars().all()
        assert len(rows) == 2


# --- L7: PII gate rejects personal names / addresses -------------------------------------


class TestPiiNameGate:
    def test_full_name_rejected(self) -> None:
        from app.core.harness.skills import pii_clean

        assert pii_clean("Applicant John Smith should click apply") is False

    def test_street_address_rejected(self) -> None:
        from app.core.harness.skills import pii_clean

        assert pii_clean("Ship to 123 Main Street then submit") is False

    def test_selector_guidance_accepted(self) -> None:
        from app.core.harness.skills import pii_clean

        assert pii_clean("Easy Apply lives at .jobs-apply-button; paginate via ?start=") is True


# --- L8: loop detection ignores same-URL modal progress ----------------------------------


class _Brain:
    def __init__(self, next_goal):
        self.next_goal = next_goal
        self.evaluation_previous_goal = None


class _Action:
    def __init__(self, name):
        self._name = name

    def model_dump(self, exclude_none=False):
        return {self._name: {}}


class _MO:
    def __init__(self, action_name, next_goal):
        self.action = [_Action(action_name)]
        self.current_state = _Brain(next_goal)


class _State:
    def __init__(self, url):
        self.url = url


class _Item:
    def __init__(self, url, action, next_goal):
        self.state = _State(url)
        self.model_output = _MO(action, next_goal)


class _RawHistory:
    def __init__(self, items):
        self.history = items

    def errors(self):
        return []

    def urls(self):
        return [i.state.url for i in self.history]

    def action_names(self):
        return []

    def model_thoughts(self):
        return []


class TestLoopDetection:
    def test_same_url_progressing_modal_is_not_a_loop(self) -> None:
        from app.core.automation.runtime import observe

        hist = _RawHistory([
            _Item("https://x/apply", "click_button", "open form"),
            _Item("https://x/apply", "input_text", "fill name"),
            _Item("https://x/apply", "click_button", "submit application"),
        ])
        assert observe.extract_run_signals(hist)["loop_detected"] is False

    def test_truly_stuck_run_is_a_loop(self) -> None:
        from app.core.automation.runtime import observe

        hist = _RawHistory([_Item("https://x", "click", "retry") for _ in range(3)])
        assert observe.extract_run_signals(hist)["loop_detected"] is True
