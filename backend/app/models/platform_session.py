"""Per-user platform browser-session metadata (assisted-login sessions, D7)."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class PlatformSession(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Tracks a user's stored browser session on a job platform.

    The encrypted browser ``storage_state`` itself lives in ``user_credentials``
    (kind=``platform_cookies``); this row holds verification/expiry metadata and the
    fingerprint used, so the worker can decide whether to reuse or prompt re-auth.
    Explicit ``user_id`` (not ``TenantMixin``): read from the worker outside tenant scope.
    """

    __tablename__ = "platform_sessions"
    __table_args__ = (UniqueConstraint("user_id", "platform", name="uq_platform_session"),)

    user_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    fingerprint_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
