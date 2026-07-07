"""Per-user LLM provider preferences (BYO-key model, decision D3).

The decrypted API key itself lives in ``user_credentials`` (kind=``llm_key``); this
table only holds the non-secret routing preferences.
"""

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserLLMConfig(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A user's preferred provider, fallback order, and default model."""

    __tablename__ = "user_llm_configs"

    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    preferred_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="openai")
    fallback_providers: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=lambda: ["groq", "openrouter"]
    )
    default_model: Mapped[str] = mapped_column(String(100), nullable=False, default="gpt-4o")
