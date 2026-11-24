"""Human-in-the-loop intervention rendezvous (CAPTCHA / 2FA pause-and-notify).

When the browser agent hits a challenge it cannot solve, the worker publishes a
``needs_intervention`` event (so the user is prompted in the UI) and then blocks waiting
for the user's response. Because the worker and API run in separate processes, the
rendezvous goes through Redis: the worker ``BLPOP``s a per-application key; the API's
``POST /applications/{id}/intervention`` ``RPUSH``es the response.
"""

from __future__ import annotations

from typing import Any, cast

from redis.asyncio import Redis


def intervention_key(application_id: str) -> str:
    return f"intervene:{application_id}"


def needs_intervention_event(application_id: str, kind: str, prompt: str) -> dict[str, Any]:
    """Build the WS event that prompts the user to resolve an intervention."""
    return {
        "type": "intervention_required",
        "payload": {"application_id": application_id, "kind": kind, "prompt": prompt},
    }


async def request_intervention(
    redis: Redis, application_id: str, *, timeout: int = 300
) -> str | None:
    """Block until the user responds (via the API) or the timeout elapses.

    Returns the user's response string, or ``None`` on timeout.
    """
    # redis-py types sync/async as a union and blpop keys as a list; runtime accepts a str.
    result = await cast(Any, redis).blpop(intervention_key(application_id), timeout=timeout)
    if result is None:
        return None
    _key, value = result
    return value.decode() if isinstance(value, bytes) else value


async def resolve_intervention(redis: Redis, application_id: str, response: str) -> None:
    """Deliver the user's intervention response to the waiting worker."""
    key = intervention_key(application_id)
    client = cast(Any, redis)  # redis-py sync/async return-type union
    await client.rpush(key, response)
    await client.expire(key, 600)
