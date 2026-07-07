"""LLM usage tracking database model."""

from sqlalchemy import Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, UUIDPrimaryKeyMixin, pg_enum
from app.models.enums import LLMPurpose


class LLMUsage(UUIDPrimaryKeyMixin, TimestampMixin, TenantMixin, Base):
    """Record of a single LLM API call for cost and usage tracking.

    ``user_id`` (from :class:`TenantMixin`) is written from the LLM call *metadata*,
    not the request contextvar — the usage callback runs in its own context.
    """

    __tablename__ = "llm_usage"
    __table_args__ = (Index("ix_llm_usage_user_created", "user_id", "created_at"),)

    # Provider info
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)

    # Token usage
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Cost
    cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Performance
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Context
    purpose: Mapped[LLMPurpose] = mapped_column(pg_enum(LLMPurpose, "llm_purpose"), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Outcome (populated by the usage callback in Phase 3)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    error: Mapped[str | None] = mapped_column(String(500), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<LLMUsage(provider='{self.provider}', model='{self.model}', "
            f"tokens={self.total_tokens}, cost=${self.cost_usd:.6f})>"
        )
