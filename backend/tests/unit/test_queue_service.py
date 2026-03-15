"""Unit tests for the queue service using fakeredis."""

import pytest
from fakeredis.aioredis import FakeRedis

from app.services import queue

QUEUE_NAME = "test:queue"


@pytest.fixture
def fake_redis():
    """Provide a FakeRedis instance for testing."""
    client = FakeRedis()
    yield client


class TestEnqueue:
    async def test_enqueue_returns_task_id(self, fake_redis):
        task_id = await queue.enqueue(fake_redis, QUEUE_NAME, {"action": "apply"})
        assert isinstance(task_id, str)
        assert len(task_id) == 32  # uuid4 hex

    async def test_enqueue_adds_to_queue(self, fake_redis):
        await queue.enqueue(fake_redis, QUEUE_NAME, {"action": "apply"})
        depth = await queue.get_queue_depth(fake_redis, QUEUE_NAME)
        assert depth == 1


class TestDequeue:
    async def test_dequeue_returns_message(self, fake_redis):
        payload = {"action": "apply", "job_id": "j1"}
        task_id = await queue.enqueue(fake_redis, QUEUE_NAME, payload)

        message = await queue.dequeue(fake_redis, QUEUE_NAME, timeout=1)
        assert message is not None
        assert message["task_id"] == task_id
        assert message["payload"] == payload
        assert "enqueued_at" in message

    async def test_dequeue_returns_none_on_empty(self, fake_redis):
        message = await queue.dequeue(fake_redis, QUEUE_NAME, timeout=1)
        assert message is None


class TestGetQueueDepth:
    async def test_depth_empty(self, fake_redis):
        depth = await queue.get_queue_depth(fake_redis, QUEUE_NAME)
        assert depth == 0

    async def test_depth_after_enqueue(self, fake_redis):
        await queue.enqueue(fake_redis, QUEUE_NAME, {"a": 1})
        await queue.enqueue(fake_redis, QUEUE_NAME, {"b": 2})
        depth = await queue.get_queue_depth(fake_redis, QUEUE_NAME)
        assert depth == 2
