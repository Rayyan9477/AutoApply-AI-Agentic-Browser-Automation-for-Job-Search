"""Queue backend abstraction (Arq now; an SQS backend can swap in behind it later)."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from arq.connections import ArqRedis


@runtime_checkable
class QueueBackend(Protocol):
    """Enqueues a named task. Returns the job id, or ``None`` on a dedup hit."""

    async def enqueue(
        self, task: str, *args: Any, job_id: str | None = None, defer: int | None = None
    ) -> str | None: ...


class ArqBackend:
    """A :class:`QueueBackend` backed by an Arq Redis pool."""

    def __init__(self, pool: ArqRedis) -> None:
        self._pool = pool

    async def enqueue(
        self, task: str, *args: Any, job_id: str | None = None, defer: int | None = None
    ) -> str | None:
        job = await self._pool.enqueue_job(task, *args, _job_id=job_id, _defer_by=defer)
        return job.job_id if job else None
