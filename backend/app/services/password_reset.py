"""Password-reset service: issue single-use tokens and redeem them.

Both entry points are enumeration-safe at the service layer: :func:`request_password_reset`
silently no-ops for an unknown/inactive email (the endpoint returns the same body either way).
"""

from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import get_settings
from app.core.exceptions import AuthError
from app.core.security import generate_reset_token, hash_password, hash_token
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import mailer

logger = structlog.get_logger(__name__)


async def request_password_reset(db: AsyncSession, email: str) -> None:
    """Issue a reset token and email a link — or silently no-op for an unknown/inactive email."""
    user = (
        await db.execute(
            select(User).where(
                User.email == email,
                User.deleted_at.is_(None),
                User.is_active.is_(True),
            )
        )
    ).scalar_one_or_none()
    if user is None:
        logger.info("password_reset_requested_unknown")  # no enumeration in logs or response
        return

    raw = generate_reset_token()
    expire_minutes = get_settings().email.reset_token_expire_minutes
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            expires_at=datetime.now(UTC) + timedelta(minutes=expire_minutes),
        )
    )
    await db.commit()
    await mailer.send_password_reset_email(user.email, mailer.build_reset_link(raw))
    logger.info("password_reset_requested", user_id=user.id)


async def reset_password(db: AsyncSession, token: str, new_password: str) -> None:
    """Redeem a reset token: set the new password, consume the token, revoke all sessions.

    Raises :class:`AuthError` (→ 401) for an unknown, expired, or already-used token.
    """
    row = (
        await db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == hash_token(token))
        )
    ).scalar_one_or_none()
    if row is None or row.used_at is not None:
        raise AuthError("Invalid or expired reset token")

    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise AuthError("Invalid or expired reset token")

    user = await db.get(User, row.user_id)
    if user is None or user.deleted_at is not None:
        raise AuthError("Invalid or expired reset token")

    now = datetime.now(UTC)
    user.hashed_password = hash_password(new_password)
    row.used_at = now
    # Consume any other outstanding reset tokens for this user, and revoke every refresh session
    # so a password reset (which may be a compromise response) invalidates all existing logins.
    await db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=now)
    )
    await db.execute(
        update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
    )
    await db.commit()
    logger.info("password_reset_completed", user_id=user.id)
