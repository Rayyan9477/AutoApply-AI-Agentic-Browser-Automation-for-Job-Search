"""Per-user settings model (one row per user; ``user_id`` is the primary key)."""

from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class UserSettings(TimestampMixin, Base):
    """A user's preferences and configuration.

    One row per user — ``user_id`` is both the PK and the FK to ``users``. Queried by
    explicit ``user_id`` (not via the tenant filter, since it is PK-scoped).
    """

    __tablename__ = "user_settings"

    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Application behavior
    apply_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="review")
    max_parallel: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    min_ats_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.75)

    # LLM preferences
    preferred_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="openai")

    # Platform config
    platforms_enabled: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["linkedin", "indeed", "glassdoor"],
    )

    # Candidate profile
    candidate_profile: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<UserSettings(user_id={self.user_id}, apply_mode='{self.apply_mode}', "
            f"provider='{self.preferred_provider}')>"
        )
