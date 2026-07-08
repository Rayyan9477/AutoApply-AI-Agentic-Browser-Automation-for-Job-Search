"""Queue backend abstraction: ArqBackend kwarg translation + return contract.

ArqBackend wraps an Arq Redis pool. Its job is to translate the *public* enqueue
surface (``job_id`` / ``defer``) into Arq's private kwargs (``_job_id`` / ``_defer_by``)
and to normalize the return into ``job.job_id`` (or ``None`` on a dedup hit, which is
what ``pool.enqueue_job`` signals by returning ``None``).

The pool is a plain MagicMock with ``enqueue_job`` as an AsyncMock -- no real Redis,
no real Arq job lifecycle is needed to assert this translation layer.
"""

from unittest.mock import AsyncMock, MagicMock

from app.services.queue_backend import ArqBackend, QueueBackend


def _backend_with_return(returned):
    """Build an ArqBackend whose pool.enqueue_job resolves to ``returned``."""
    pool = MagicMock()
    pool.enqueue_job = AsyncMock(return_value=returned)
    return ArqBackend(pool), pool


class TestEnqueueKwargTranslation:
    async def test_translates_public_kwargs_to_arq_private_kwargs(self):
        job = MagicMock(job_id="abc123")
        backend, pool = _backend_with_return(job)

        await backend.enqueue("run_apply", 7, "extra", job_id="my-dedup-key", defer=30)

        pool.enqueue_job.assert_awaited_once_with(
            "run_apply",
            7,
            "extra",
            _job_id="my-dedup-key",
            _defer_by=30,
        )

    async def test_defaults_translate_to_none_arq_kwargs(self):
        # No job_id / defer supplied -> both private kwargs must still be passed as None,
        # since Arq treats absent _job_id (auto-gen) and explicit None identically here.
        job = MagicMock(job_id="auto")
        backend, pool = _backend_with_return(job)

        await backend.enqueue("send_email")

        pool.enqueue_job.assert_awaited_once_with(
            "send_email",
            _job_id=None,
            _defer_by=None,
        )

    async def test_does_not_leak_public_kwarg_names_to_arq(self):
        # Arq's enqueue_job has no `job_id`/`defer` params; leaking them would TypeError
        # in production. Guard the translation by asserting the public names never appear.
        backend, pool = _backend_with_return(MagicMock(job_id="x"))

        await backend.enqueue("task", job_id="k", defer=5)

        _, kwargs = pool.enqueue_job.call_args
        assert "job_id" not in kwargs
        assert "defer" not in kwargs
        assert kwargs == {"_job_id": "k", "_defer_by": 5}

    async def test_positional_args_forwarded_in_order(self):
        backend, pool = _backend_with_return(MagicMock(job_id="x"))

        await backend.enqueue("task", "a", "b", "c")

        args, _ = pool.enqueue_job.call_args
        assert args == ("task", "a", "b", "c")


class TestEnqueueReturnContract:
    async def test_returns_job_id_when_job_returned(self):
        backend, _ = _backend_with_return(MagicMock(job_id="job-42"))

        result = await backend.enqueue("task")

        assert result == "job-42"

    async def test_returns_none_on_dedup_hit(self):
        # Arq returns None from enqueue_job when a job with the same _job_id is already
        # queued/in-flight (dedup). ArqBackend must surface that as None, not raise.
        backend, _ = _backend_with_return(None)

        result = await backend.enqueue("task", job_id="duplicate")

        assert result is None

    async def test_return_value_is_the_jobs_id_not_a_truthy_proxy(self):
        # Make sure it returns the *attribute*, not the job object itself.
        job = MagicMock(job_id="the-id")
        backend, _ = _backend_with_return(job)

        result = await backend.enqueue("task")

        assert result == "the-id"
        assert result is not job


class TestProtocolConformance:
    def test_arqbackend_is_a_queue_backend(self):
        # QueueBackend is runtime_checkable; ArqBackend exposes async enqueue(...).
        backend = ArqBackend(MagicMock())
        assert isinstance(backend, QueueBackend)

    def test_object_missing_enqueue_is_not_a_queue_backend(self):
        # Negative case: the structural check actually discriminates.
        assert not isinstance(object(), QueueBackend)
