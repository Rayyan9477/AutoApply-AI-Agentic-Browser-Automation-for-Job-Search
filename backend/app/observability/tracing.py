"""LLM call tracing for cost and latency observability."""

import uuid
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import UTC, datetime

import structlog

logger = structlog.get_logger(__name__)

# Context variable for per-request trace ID
current_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """Generate a unique trace ID for an application session."""
    return f"autoapply-{uuid.uuid4().hex[:12]}"


def set_trace_id(trace_id: str | None = None) -> str:
    """Set trace ID in current context. Generates one if not provided."""
    tid = trace_id or generate_trace_id()
    current_trace_id.set(tid)
    return tid


def get_trace_id() -> str:
    """Get current trace ID from context."""
    return current_trace_id.get()


@dataclass
class LLMCallRecord:
    """Record of a single LLM API call for tracing."""

    trace_id: str
    provider: str
    model: str
    purpose: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
    status: str = "success"
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def log(self) -> None:
        """Log this call record with structlog."""
        logger.info(
            "llm_call_completed",
            trace_id=self.trace_id,
            provider=self.provider,
            model=self.model,
            purpose=self.purpose,
            prompt_tokens=self.prompt_tokens,
            completion_tokens=self.completion_tokens,
            cost_usd=round(self.cost_usd, 6),
            latency_ms=self.latency_ms,
            status=self.status,
        )
