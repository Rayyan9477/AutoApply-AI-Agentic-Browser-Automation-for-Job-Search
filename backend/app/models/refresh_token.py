"""Refresh-token model. The table ships in Phase 0; rotation logic lands in Phase 1."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class RefreshToken(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A hashed, rotating refresh token bound to a token family for reuse-detection.

    Uses an explicit ``user_id`` column (not ``TenantMixin``): refresh lookups happen
    before a tenant context exists, so they must not be subject to the SELECT filter.
    """

    __tablename__ = "refresh_tokens"

    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    family_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
