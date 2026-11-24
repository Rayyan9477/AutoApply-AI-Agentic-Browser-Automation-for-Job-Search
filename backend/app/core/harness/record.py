"""Persistence helpers for harness artifacts (trajectory, verdict, diagnosis)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.harness.diagnose import Diagnosis
from app.core.harness.judge import JudgeOutput
from app.models.harness import RunDiagnosis, RunTrajectory, RunVerdict


async def record_trajectory(
    db: AsyncSession,
    *,
    user_id: str,
    application_id: str,
    platform: str,
    steps: list[Any] | None = None,
    screenshots: list[Any] | None = None,
    agent_self_report: str | None = None,
    tokens: int = 0,
    cost_usd: float = 0.0,
    duration_ms: int = 0,
    status: str = "completed",
    skills_used: list[str] | None = None,
) -> RunTrajectory:
    traj = RunTrajectory(
        user_id=user_id,
        application_id=application_id,
        platform=platform,
        steps=steps or [],
        screenshots=screenshots or [],
        agent_self_report=agent_self_report,
        tokens=tokens,
        cost_usd=cost_usd,
        duration_ms=duration_ms,
        status=status,
        skills_used=skills_used or [],
    )
    db.add(traj)
    await db.commit()
    await db.refresh(traj)
    return traj


async def record_verdict(
    db: AsyncSession, *, user_id: str, run_id: str, judge: JudgeOutput, model: str | None = None
) -> RunVerdict:
    verdict = RunVerdict(
        user_id=user_id,
        run_id=run_id,
        verdict=judge.verdict,
        confidence=judge.confidence,
        reason=judge.reason,
        judged_model=model,
    )
    db.add(verdict)
    await db.commit()
    await db.refresh(verdict)
    return verdict


async def record_diagnosis(
    db: AsyncSession,
    *,
    user_id: str,
    run_id: str,
    diagnosis: Diagnosis,
    signals: dict[str, Any] | None = None,
) -> RunDiagnosis:
    row = RunDiagnosis(
        user_id=user_id,
        run_id=run_id,
        failure_class=diagnosis.failure_class,
        root_cause=diagnosis.root_cause,
        signals=signals or {},
        suggested_action=diagnosis.suggested_action,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row
