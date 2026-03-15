"""Redis-based task queue service.

Provides simple enqueue/dequeue operations for background job processing.
Workers consume from these queues to apply to jobs, scrape listings, etc.
"""

import json
import uuid
from datetime import UTC, datetime

import structlog
from redis.asyncio import Redis

logger = structlog.get_logger(__name__)


async def enqueue(
    redis: Redis,
    queue_name: str,
    payload: dict,
) -> str:
    """Push a task onto a Redis queue.

    Args:
        redis: Async Redis client.
        queue_name: Name of the Redis list to push to.
        payload: Task data to serialize as JSON.

    Returns:
        Unique task ID assigned to the enqueued task.
    """
    task_id = uuid.uuid4().hex
    message = {
        "task_id": task_id,
        "payload": payload,
        "enqueued_at": datetime.now(UTC).isoformat(),
    }
    await redis.rpush(queue_name, json.dumps(message))
    logger.info("task_enqueued", task_id=task_id, queue=queue_name)
    return task_id


async def dequeue(
    redis: Redis,
    queue_name: str,
    timeout: int = 5,
) -> dict | None:
    """Pop a task from a Redis queue (blocking).

    Args:
        redis: Async Redis client.
        queue_name: Name of the Redis list to pop from.
        timeout: Blocking timeout in seconds.

    Returns:
        Deserialized task dict, or None if timeout expired.
    """
    result = await redis.blpop(queue_name, timeout=timeout)
    if result is None:
        return None

    _queue, raw = result
    message = json.loads(raw)
    logger.debug("task_dequeued", task_id=message.get("task_id"), queue=queue_name)
    return message


async def get_queue_depth(redis: Redis, queue_name: str) -> int:
    """Get the number of pending tasks in a queue.

    Args:
        redis: Async Redis client.
        queue_name: Name of the Redis list.

    Returns:
        Number of items currently in the queue.
    """
    return await redis.llen(queue_name)
