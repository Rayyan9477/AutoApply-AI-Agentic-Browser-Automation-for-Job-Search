"""Single-use password-reset token (hashed at rest, like the refresh token)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PasswordResetToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An opaque, single-use reset token stored only as a SHA-256 hash.

    Explicit ``user_id`` (not ``TenantMixin``): the reset flow runs before any authenticated
    tenant context exists, so lookups must not be subject to the SELECT filter. ``used_at`` is
    stamped when the token is redeemed, making it single-use.
    """

    __tablename__ = "password_reset_tokens"

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
