"""Unit tests for app.observability.tracing."""

from __future__ import annotations

from app.observability.tracing import (
    LLMCallRecord,
    generate_trace_id,
    get_trace_id,
    set_trace_id,
)


class TestTraceIdManagement:
    def test_generate_trace_id_format(self):
        tid = generate_trace_id()
        assert tid.startswith("autoapply-")
        assert len(tid) > 20

    def test_set_and_get_trace_id(self):
        tid = set_trace_id("custom-trace-123")
        assert tid == "custom-trace-123"
        assert get_trace_id() == "custom-trace-123"

    def test_set_trace_id_auto_generates(self):
        tid = set_trace_id()
        assert tid.startswith("autoapply-")
        assert get_trace_id() == tid


class TestLLMCallRecord:
    def test_create_record(self):
        record = LLMCallRecord(
            trace_id="t-1",
            provider="openai",
            model="gpt-4",
            purpose="resume_generation",
            prompt_tokens=100,
            completion_tokens=200,
            total_tokens=300,
            cost_usd=0.01,
            latency_ms=500,
        )
        assert record.status == "success"
        assert record.error is None

    def test_log_does_not_raise(self):
        record = LLMCallRecord(
            trace_id="t-2",
            provider="anthropic",
            model="claude",
            purpose="scoring",
        )
        record.log()  # should not raise
