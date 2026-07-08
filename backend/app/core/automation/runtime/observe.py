"""Observe a browser-use apply run: per-step progress + post-run trajectory/signals.

All history access is DUCK-TYPED (no ``browser_use`` import) so this module is import-safe
in CI and the pure extractors can be unit-tested with a fake history. ``make_step_observer``
returns the async ``on_step_end(agent)`` hook passed to ``Agent.run(on_step_end=...)``.

The two extractors map a browser-use ``AgentHistoryList`` onto (1) the ``signals`` dict the
harness ``diagnose()`` consumes and (2) the ``record_trajectory(**kwargs)`` fields.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any

import structlog

from app.api.websocket.bus import publish_progress
from app.observability.metrics import browser_actions_total

logger = structlog.get_logger(__name__)

_MAX_STEPS_STORED = 100
_MAX_SCREENSHOTS = 20
_LOOP_REPEAT = 3  # N identical trailing urls/actions ⇒ the agent is looping


def _call(history: Any, name: str, default: Any) -> Any:
    """Call ``history.name()`` if present and callable, else return ``default``."""
    fn = getattr(history, name, None)
    if callable(fn):
        try:
            return fn()
        except Exception:  # a defensive read must never raise into the apply path
            return default
    return default


def _detect_loop(*sequences: list[Any]) -> bool:
    for seq in sequences:
        tail = [s for s in seq if s][-_LOOP_REPEAT:]
        if len(tail) == _LOOP_REPEAT and len(set(tail)) == 1:
            return True
    return False


def _action_name_of(model_output: Any) -> str | None:
    """The first action's name for one step's model_output (mirrors action_names())."""
    for action in getattr(model_output, "action", None) or []:
        dump = getattr(action, "model_dump", None)
        if callable(dump):
            try:
                keys = [k for k in dump(exclude_none=True) if k != "interacted_element"]
            except Exception:
                continue
            if keys:
                return str(keys[0])
    return None


def _build_steps(history: Any) -> list[dict[str, Any]]:
    """One row per real step. Prefer the raw per-item history (action/url/eval all from
    the SAME step); fall back to a positional zip only when the flat lists are full-length.

    browser-use's ``action_names()`` is per-action (cumulative, multi-per-step) and
    ``model_thoughts()`` drops no-output steps, so they are NOT index-aligned with the
    per-step ``urls()``/``number_of_steps()``; zipping them by index misattributes data.
    """
    raw_items = getattr(history, "history", None)
    steps: list[dict[str, Any]] = []
    if isinstance(raw_items, list):
        for i, item in enumerate(raw_items[:_MAX_STEPS_STORED]):
            model_output = getattr(item, "model_output", None)
            state = getattr(item, "state", None)
            brain = getattr(model_output, "current_state", None) if model_output else None
            steps.append(
                {
                    "n": i + 1,
                    "action": _action_name_of(model_output) if model_output else None,
                    "url": getattr(state, "url", None),
                    "evaluation": getattr(brain, "evaluation_previous_goal", None),
                    "next_goal": getattr(brain, "next_goal", None),
                }
            )
        return steps

    # Fallback (minimal/duck-typed history): only trust positional alignment when the
    # filtered lists match the step count; otherwise leave action/eval None rather than
    # borrowing a different step's data.
    actions = _call(history, "action_names", []) or []
    urls = _call(history, "urls", []) or []
    thoughts = _call(history, "model_thoughts", []) or []
    n = int(_call(history, "number_of_steps", len(actions)) or len(actions))
    aligned = len(actions) == n and len(thoughts) == n
    for i in range(min(n, _MAX_STEPS_STORED)):
        thought = thoughts[i] if (aligned and i < len(thoughts)) else None
        steps.append(
            {
                "n": i + 1,
                "action": actions[i] if (aligned and i < len(actions)) else None,
                "url": urls[i] if i < len(urls) else None,
                "evaluation": getattr(thought, "evaluation_previous_goal", None),
                "next_goal": getattr(thought, "next_goal", None),
            }
        )
    return steps


def _current_step_actions(history: Any) -> list[str]:
    """Names of the actions executed in the LATEST step only (for per-action metrics).

    Prefers the per-step ``action_history()`` (nested list); falls back to the cumulative
    ``action_names()`` tail so the observer still works against a minimal/fake history.
    """
    per_step = _call(history, "action_history", None)
    if isinstance(per_step, list) and per_step and isinstance(per_step[-1], list):
        names: list[str] = []
        for a in per_step[-1]:
            if isinstance(a, dict):
                key = next((k for k in a if k not in ("interacted_element", "result")), None)
                if key:
                    names.append(str(key))
        if names:
            return names
    flat = _call(history, "action_names", []) or []
    return [str(flat[-1])] if flat else []


def extract_run_signals(history: Any) -> dict[str, Any]:
    """Build the signals dict consumed by ``diagnose()`` from an AgentHistoryList."""
    raw_errors = _call(history, "errors", []) or []
    errors = [e for e in raw_errors if e]
    urls = [u for u in (_call(history, "urls", []) or []) if u]
    evaluations = [
        getattr(t, "evaluation_previous_goal", None)
        for t in (_call(history, "model_thoughts", []) or [])
    ]

    # consecutive failures = the trailing run of non-empty per-step errors
    consecutive = 0
    for err in reversed(raw_errors):
        if err:
            consecutive += 1
        else:
            break

    # Loop detection on a per-step composite (url + action + next_goal) rather than URL alone:
    # modal/SPA apply forms (e.g. LinkedIn Easy Apply) keep the same URL while progressing, so a
    # URL-only check misreads a normal multi-step fill as a loop. Fall back to URLs when no
    # per-step structure is available.
    steps = _build_steps(history)
    step_keys = (
        [f"{s.get('url')}|{s.get('action')}|{s.get('next_goal')}" for s in steps]
        if steps
        else urls
    )

    joined = " ".join(errors).lower()
    signals: dict[str, Any] = {
        "errors": errors,
        "evaluations": [e for e in evaluations if e],
        "consecutive_failures": consecutive,
        "loop_detected": _detect_loop(step_keys),
        "timed_out": "timeout" in joined or "timed out" in joined,
        "llm_error": "llm" in joined or "rate limit" in joined,
    }
    if urls:
        signals["final_url"] = urls[-1]
    return signals


def extract_trajectory(history: Any) -> dict[str, Any]:
    """Build ``record_trajectory(**kwargs)`` from an AgentHistoryList."""
    steps = _build_steps(history)
    screenshots = [s for s in (_call(history, "screenshot_paths", []) or []) if s]

    usage = getattr(history, "usage", None)
    done = bool(_call(history, "is_done", False))
    successful = _call(history, "is_successful", None)

    return {
        "steps": steps,
        "screenshots": screenshots[:_MAX_SCREENSHOTS],
        "agent_self_report": _call(history, "final_result", None),
        "tokens": int(getattr(usage, "total_tokens", 0) or 0),
        "cost_usd": float(getattr(usage, "total_cost", 0.0) or 0.0),
        "duration_ms": int((_call(history, "total_duration_seconds", 0.0) or 0.0) * 1000),
        "status": "completed" if (done and successful is not False) else "failed",
    }


StepHook = Callable[[Any], Awaitable[None]]


def make_step_observer(
    redis: Any, user_id: str, application_id: str, platform: str
) -> StepHook:
    """Return an async ``on_step_end(agent)`` hook: emit a browser-action metric + WS progress."""

    async def on_step_end(agent: Any) -> None:
        try:
            history = getattr(agent, "history", None)
            actions = _current_step_actions(history) if history is not None else []
            if not actions:
                actions = ["step"]
            for name in actions:  # one increment per action this step (not per step)
                browser_actions_total.labels(platform=platform, action=name).inc()
            if redis is not None:
                step_n = _call(history, "number_of_steps", 0) if history is not None else 0
                await publish_progress(
                    redis,
                    user_id,
                    {
                        "type": "application_progress",
                        "payload": {
                            "application_id": application_id,
                            "status": "applying",
                            "detail": f"step {step_n}: {actions[-1]}",
                        },
                    },
                )
        except Exception as exc:  # an observer must never abort the agent run
            logger.debug("observe.step_hook_failed", error=str(exc))

    return on_step_end
