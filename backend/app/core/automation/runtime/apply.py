"""The live apply pipeline step (browser-use).

``run_apply`` first checks all prerequisites (job, resume file, a saved platform session,
and an LLM key) — that part is unit-tested. Only when they're satisfied does it drive a
real browser via browser-use, which requires a headful/Xvfb environment and a valid
assisted-login session, and is exercised through ``scripts/spike_apply.py`` rather than CI.
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.automation.runtime.factory import (
    build_apply_agent,
    build_apply_llm,
    build_browser_profile,
)
from app.core.automation.runtime.observe import (
    extract_run_signals,
    extract_trajectory,
    make_step_observer,
)
from app.core.automation.runtime.result import ApplicationResult
from app.core.harness.record import record_trajectory
from app.core.harness.skills import build_skill_guidance, load_skills
from app.core.secrets import CredentialStore
from app.core.storage import StorageService, get_storage
from app.db.session import async_session_factory
from app.models.application import Application
from app.models.job import Job
from app.models.resume import Resume
from app.models.user_llm_config import UserLLMConfig
from app.observability.metrics import browser_session_duration_seconds
from app.services.dispatch import REVIEW_TASK

logger = structlog.get_logger(__name__)

_GUARDRAILS = (
    "You are applying to a single job on behalf of the user. Only fill fields with the "
    "user's real resume data; never invent answers. If you hit a CAPTCHA, a 2FA prompt, "
    "or a login wall, stop and report that human intervention is required — do not guess. "
    "When the application is submitted, report the confirmation in the structured output."
)


class ApplyPrerequisiteError(Exception):
    """A required input is missing (no session, no key, no resume) — setup needed."""


def _build_task(job: Job, resume_path: str) -> str:
    return (
        f"Apply to this job on {job.platform}:\n"
        f"Title: {job.title}\nCompany: {job.company}\nURL: {job.url}\n\n"
        f"Use the resume file at: {resume_path}\n"
        "Navigate to the job, complete the application form, upload the resume, and submit."
    )


def _extract_result(history: object) -> ApplicationResult:
    # browser-use's ``structured_output`` is a property that re-validates the agent's
    # done-text against ApplicationResult; on malformed text it raises ValidationError
    # (a ValueError, NOT AttributeError), which getattr would NOT swallow.
    try:
        out = getattr(history, "structured_output", None)
    except Exception:
        out = None
    if isinstance(out, ApplicationResult):
        return out
    final = history.final_result() if hasattr(history, "final_result") else None
    return ApplicationResult(submitted=bool(final), notes=str(final or "")[:500])


async def run_apply(
    db: AsyncSession, app: Application, *, redis: Any | None = None
) -> ApplicationResult:
    """Drive a real browser to submit ``app``. Raises ApplyPrerequisiteError if not set up.

    When ``redis`` (the Arq pool) is provided, each step publishes live progress, and the
    run's trajectory is persisted and handed to the self-evolving harness via a follow-on
    review job. ``redis`` is None in the standalone spike and in CI.
    """
    job = await db.get(Job, app.job_id)
    if job is None:
        raise ApplyPrerequisiteError("Job not found")
    resume = await db.get(Resume, app.resume_id) if app.resume_id else None
    if resume is None:
        raise ApplyPrerequisiteError("Application has no resume attached")
    resume_key = resume.file_path_pdf or resume.file_path_docx
    if not resume_key:
        raise ApplyPrerequisiteError("Resume file is not available")

    store = CredentialStore()
    storage_state = await store.load_session_cookies(db, app.user_id, job.platform)
    if storage_state is None:
        raise ApplyPrerequisiteError(
            f"No saved {job.platform} session — assisted login required"
        )

    cfg = (
        await db.execute(select(UserLLMConfig).where(UserLLMConfig.user_id == app.user_id))
    ).scalar_one_or_none()
    llm_settings = get_settings().llm
    provider = cfg.preferred_provider if cfg else llm_settings.preferred_provider
    model = cfg.default_model if cfg else llm_settings.default_model
    # Bedrock is platform-authenticated (AWS credential chain) — it needs no per-user key.
    is_bedrock = provider == "bedrock" or model.startswith("bedrock/")
    api_key = None if is_bedrock else await store.get_llm_key(db, app.user_id, provider)
    if not is_bedrock and not api_key:
        raise ApplyPrerequisiteError("No LLM API key configured for the user")

    # --- Prerequisites satisfied; drive the browser (real-browser spike path) ---
    # Inject any active, learned site-skills into the agent's system prompt, and remember
    # which were used so the run's verdict can feed back to score them.
    loaded_skills = await load_skills(db, job.platform)
    skill_ids = [skill.id for skill in loaded_skills]
    guidance = build_skill_guidance(loaded_skills)
    extend = f"{_GUARDRAILS}\n\n{guidance}" if guidance else _GUARDRAILS

    # Materialize the stored resume to a local temp file the browser can upload.
    resume_path = await StorageService(get_storage(), app.user_id).materialize_to_temp(
        resume_key, suffix=Path(resume_key).suffix or ".pdf"
    )

    profile = build_browser_profile(
        storage_state=storage_state,
        allowed_domains=[f"https://*.{job.platform}.com", f"https://{job.platform}.com"],
    )
    llm = build_apply_llm(api_key, model)
    agent = build_apply_agent(
        _build_task(job, resume_path), llm=llm, profile=profile, extend_system_message=extend
    )
    on_step_end = make_step_observer(redis, app.user_id, app.id, job.platform)

    # browser-use's Agent.run RE-RAISES infrastructure failures (CDP/browser crash,
    # network, LLM auth) instead of returning a history. Capture both outcomes so the
    # self-evolving harness still records and learns from the worst failures.
    start = time.perf_counter()
    history: object | None = None
    run_error: Exception | None = None
    try:
        history = await agent.run(
            max_steps=get_settings().browser.max_steps, on_step_end=on_step_end
        )
    except Exception as exc:
        run_error = exc
    finally:
        browser_session_duration_seconds.labels(platform=job.platform).observe(
            time.perf_counter() - start
        )
        # The résumé was materialized from storage to a temp file for the upload; remove it.
        with contextlib.suppress(OSError):
            os.remove(resume_path)

    # Persist + review on BOTH the success and the raise paths.
    await _record_and_review(
        app, job.platform, history, redis, error=run_error, skills_used=skill_ids
    )

    if run_error is not None:
        logger.warning("apply.run_failed", application_id=app.id, error=str(run_error))
        raise run_error

    result = _extract_result(history)
    logger.info("apply.run_complete", application_id=app.id, submitted=result.submitted)
    return result


async def _record_and_review(
    app: Application,
    platform: str,
    history: object,
    redis: Any | None,
    *,
    error: Exception | None = None,
    skills_used: list[str] | None = None,
) -> None:
    """Persist the run trajectory and enqueue the harness review (best-effort).

    Uses a DEDICATED session (not the worker's load-bearing apply session) so a trajectory
    commit failure can never poison the apply transaction. Observability must never break
    the apply result, so failures here are swallowed. A raised ``error`` is folded into the
    trajectory/signals so ``diagnose()`` can classify it rather than defaulting to UNKNOWN.
    """
    try:
        traj_kwargs = extract_trajectory(history)
        signals = extract_run_signals(history)
        if error is not None:
            msg = str(error)
            low = msg.lower()
            traj_kwargs["status"] = "failed"
            traj_kwargs["agent_self_report"] = (
                f"{traj_kwargs.get('agent_self_report') or ''}\nRUN RAISED: "
                f"{type(error).__name__}: {msg}"
            ).strip()[:1000]
            signals.setdefault("errors", []).append(msg)
            signals["llm_error"] = signals.get("llm_error") or any(
                w in low for w in ("llm", "api key", "rate limit", "401", "auth")
            )
            signals["timed_out"] = signals.get("timed_out") or (
                "timeout" in low or "timed out" in low
            )
        async with async_session_factory() as obs_db:
            traj = await record_trajectory(
                obs_db, user_id=app.user_id, application_id=app.id,
                platform=platform, skills_used=skills_used, **traj_kwargs,
            )
            traj_id = traj.id
        if redis is not None:
            await redis.enqueue_job(
                REVIEW_TASK, traj_id, signals, _job_id=f"review:{traj_id}"
            )
    except Exception as exc:  # observability is best-effort, not load-bearing
        logger.warning("apply.record_and_review_failed", application_id=app.id, error=str(exc))
