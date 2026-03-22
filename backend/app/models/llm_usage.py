"""LLM usage tracking database model."""

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class LLMUsage(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Record of a single LLM API call for cost and usage tracking."""

    __tablename__ = "llm_usage"

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
    purpose: Mapped[str] = mapped_column(String(50), nullable=False)
    trace_id: Mapped[str | None] = mapped_column(String(100), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<LLMUsage(provider='{self.provider}', model='{self.model}', "
            f"tokens={self.total_tokens}, cost=${self.cost_usd:.6f})>"
        )
