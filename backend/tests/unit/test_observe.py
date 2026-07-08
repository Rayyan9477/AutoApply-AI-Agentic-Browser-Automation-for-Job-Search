"""Phase 3: browser-run observation — signal/trajectory extraction + step observer.

History is duck-typed in observe.py, so a FakeHistory exercises the real extractors
without browser-use. FakeHistory is reused by test_run_apply_harness.
"""

from unittest.mock import MagicMock

import fakeredis.aioredis

from app.core.automation.runtime import observe


class _Thought:
    def __init__(self, evaluation_previous_goal=None, next_goal=None):
        self.evaluation_previous_goal = evaluation_previous_goal
        self.next_goal = next_goal


class _Usage:
    total_tokens = 1234
    total_cost = 0.0456


class FakeHistory:
    """Duck-typed stand-in for browser-use AgentHistoryList."""

    def __init__(
        self, *, errors=None, urls=None, actions=None, thoughts=None, done=True,
        successful=True, steps=None, duration=2.5, usage=None, final="Applied successfully",
        screenshots=None,
    ):
        self._errors = errors if errors is not None else []
        self._urls = urls or []
        self._actions = actions or []
        self._thoughts = thoughts or []
        self._done = done
        self._successful = successful
        self._steps = steps if steps is not None else len(self._actions)
        self._duration = duration
        self.usage = usage if usage is not None else _Usage()
        self._final = final
        self._screenshots = screenshots or []

    def errors(self):
        return self._errors

    def urls(self):
        return self._urls

    def action_names(self):
        return self._actions

    def model_thoughts(self):
        return self._thoughts

    def number_of_steps(self):
        return self._steps

    def total_duration_seconds(self):
        return self._duration

    def final_result(self):
        return self._final

    def is_done(self):
        return self._done

    def is_successful(self):
        return self._successful

    def screenshot_paths(self):
        return self._screenshots


class TestExtractSignals:
    def test_errors_and_consecutive_failures(self):
        sig = observe.extract_run_signals(
            FakeHistory(errors=[None, "boom", "element not found: #x"])
        )
        assert sig["errors"] == ["boom", "element not found: #x"]
        assert sig["consecutive_failures"] == 2

    def test_consecutive_resets_after_a_clean_step(self):
        assert observe.extract_run_signals(FakeHistory(errors=["boom", None]))[
            "consecutive_failures"
        ] == 0

    def test_final_url_and_loop_detection(self):
        sig = observe.extract_run_signals(
            FakeHistory(urls=["https://x/login", "https://x/login", "https://x/login"])
        )
        assert sig["final_url"] == "https://x/login"
        assert sig["loop_detected"] is True

    def test_no_loop_when_varied(self):
        sig = observe.extract_run_signals(
            FakeHistory(urls=["a", "b", "c"], actions=["click", "type", "submit"])
        )
        assert sig["loop_detected"] is False

    def test_timed_out_from_error_text(self):
        assert observe.extract_run_signals(FakeHistory(errors=["step timeout exceeded"]))[
            "timed_out"
        ] is True


class TestExtractTrajectory:
    def test_fields(self):
        t = observe.extract_trajectory(
            FakeHistory(
                actions=["go_to_url", "done"],
                urls=["https://x/job", "https://x/confirm"],
                thoughts=[_Thought("ok", "click apply"), _Thought("submitted", "done")],
                duration=3.0,
            )
        )
        assert t["tokens"] == 1234
        assert t["cost_usd"] == 0.0456
        assert t["duration_ms"] == 3000
        assert t["status"] == "completed"
        assert t["agent_self_report"] == "Applied successfully"
        assert len(t["steps"]) == 2
        assert t["steps"][0]["action"] == "go_to_url"
        assert t["steps"][1]["next_goal"] == "done"

    def test_status_failed_when_not_successful(self):
        assert observe.extract_trajectory(FakeHistory(done=True, successful=False))[
            "status"
        ] == "failed"

    def test_handles_minimal_history_without_raising(self):
        t = observe.extract_trajectory(object())
        assert t["status"] == "failed" and t["steps"] == [] and t["tokens"] == 0


class TestStepObserver:
    async def test_emits_metric_and_publishes(self):
        redis = fakeredis.aioredis.FakeRedis()
        agent = MagicMock()
        agent.history = FakeHistory(actions=["click_element"], steps=1)
        gauge = observe.browser_actions_total.labels(platform="linkedin", action="click_element")
        before = gauge._value.get()

        hook = observe.make_step_observer(redis, "u1", "app1", "linkedin")
        await hook(agent)

        assert gauge._value.get() == before + 1

    async def test_never_raises_on_bad_agent(self):
        hook = observe.make_step_observer(None, "u1", "app1", "linkedin")
        await hook(object())  # no .history, redis None — must be a silent no-op

    async def test_multi_action_step_increments_per_action(self):
        agent = MagicMock()
        agent.history = _ActionHistory([[{"input_text": {}}, {"click_element": {}}]])
        it = observe.browser_actions_total.labels(platform="indeed", action="input_text")
        cl = observe.browser_actions_total.labels(platform="indeed", action="click_element")
        b_it, b_cl = it._value.get(), cl._value.get()

        await observe.make_step_observer(None, "u", "a", "indeed")(agent)

        assert it._value.get() == b_it + 1
        assert cl._value.get() == b_cl + 1


# ---------------------------------------------------------------------------
# Raw per-item history → step alignment (the bug the positional-zip fix addresses)
# ---------------------------------------------------------------------------


class _State:
    def __init__(self, url):
        self.url = url


class _Brain:
    def __init__(self, evaluation_previous_goal=None, next_goal=None):
        self.evaluation_previous_goal = evaluation_previous_goal
        self.next_goal = next_goal


class _Action:
    def __init__(self, name):
        self._name = name

    def model_dump(self, exclude_none=True):
        return {self._name: {}}


class _ModelOutput:
    def __init__(self, actions, brain):
        self.action = actions
        self.current_state = brain


class _Item:
    def __init__(self, url, model_output=None):
        self.state = _State(url)
        self.model_output = model_output


class _ActionHistory:
    """Minimal history exposing action_history() for the per-action observer test."""

    def __init__(self, action_history):
        self._ah = action_history

    def action_history(self):
        return self._ah

    def number_of_steps(self):
        return len(self._ah)


class RawHistory:
    """History exposing raw .history items (the real browser-use shape)."""

    def __init__(self, items):
        self.history = items
        self.usage = _Usage()

    def screenshot_paths(self):
        return []

    def total_duration_seconds(self):
        return 1.0

    def is_done(self):
        return True

    def is_successful(self):
        return True


class TestStepAlignment:
    def test_no_output_step_does_not_shift_later_rows(self):
        items = [
            _Item("u0", _ModelOutput([_Action("go_to_url")], _Brain("ok", "g0"))),
            _Item("u1", model_output=None),  # transient LLM-parse failure mid-run
            _Item("u2", _ModelOutput([_Action("input_text"), _Action("click")], _Brain("e2", "g2"))),
        ]
        steps = observe.extract_trajectory(RawHistory(items))["steps"]

        assert [s["url"] for s in steps] == ["u0", "u1", "u2"]  # per-step urls intact
        assert steps[1]["action"] is None and steps[1]["evaluation"] is None  # not borrowed
        assert steps[2]["action"] == "input_text"  # first action of its own step
        assert steps[2]["next_goal"] == "g2"
