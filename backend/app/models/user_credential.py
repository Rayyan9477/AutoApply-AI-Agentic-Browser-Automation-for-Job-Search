"""Per-user encrypted credentials: BYO LLM keys and platform session cookies.

No platform passwords are ever stored (decision D7) — only ``llm_key`` and
``platform_cookies`` (an encrypted browser ``storage_state``). The ``blob`` column
holds a serialized ``EncryptedBlob``; plaintext never touches the DB or logs.
"""

from typing import Any

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class UserCredential(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """An envelope-encrypted secret owned by a user.

    Explicit ``user_id`` (not ``TenantMixin``): credential reads pass ``user_id``
    explicitly and may run outside a tenant context (e.g. in the worker / LLM
    callback), so they must not depend on the ambient SELECT filter.
    """

    __tablename__ = "user_credentials"
    __table_args__ = (
        UniqueConstraint("user_id", "kind", "provider", name="uq_user_credential"),
    )

    user_id: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)  # llm_key | platform_cookies
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    blob: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    kek_id: Mapped[str] = mapped_column(String(64), nullable=False)
