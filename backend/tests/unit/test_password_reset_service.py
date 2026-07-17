"""Unit tests for the password-reset service (expiry, single-use, no-enumeration)."""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import AuthError
from app.core.security import hash_password, hash_token, verify_password
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services import password_reset


async def _make_user(db, email="pr@x.com", password="password123") -> User:
    user = User(email=email, hashed_password=hash_password(password), is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


class TestRequestPasswordReset:
    async def test_no_op_for_unknown_email(self, db_session, monkeypatch):
        sent: list[str] = []

        async def _capture(to: str, reset_link: str) -> None:
            sent.append(reset_link)

        monkeypatch.setattr(password_reset.mailer, "send_password_reset_email", _capture)
        await password_reset.request_password_reset(db_session, "ghost@x.com")
        assert sent == []

    async def test_creates_single_use_token_and_emails_link(self, db_session, monkeypatch):
        user = await _make_user(db_session)
        links: list[str] = []

        async def _capture(to: str, reset_link: str) -> None:
            links.append(reset_link)

        monkeypatch.setattr(password_reset.mailer, "send_password_reset_email", _capture)
        await password_reset.request_password_reset(db_session, user.email)
        assert len(links) == 1 and "token=" in links[0]


class TestResetPassword:
    async def test_rejects_expired_token(self, db_session):
        user = await _make_user(db_session)
        raw = "expired-token-value-1234567890"
        db_session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        await db_session.commit()
        with pytest.raises(AuthError):
            await password_reset.reset_password(db_session, raw, "newpassword456")

    async def test_rejects_used_token(self, db_session):
        user = await _make_user(db_session)
        raw = "used-token-value-1234567890abc"
        db_session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
                used_at=datetime.now(UTC),
            )
        )
        await db_session.commit()
        with pytest.raises(AuthError):
            await password_reset.reset_password(db_session, raw, "newpassword456")

    async def test_valid_token_updates_hash_and_marks_used(self, db_session):
        user = await _make_user(db_session)
        raw = "valid-token-value-1234567890abc"
        db_session.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=hash_token(raw),
                expires_at=datetime.now(UTC) + timedelta(minutes=30),
            )
        )
        await db_session.commit()

        await password_reset.reset_password(db_session, raw, "newpassword456")
        await db_session.refresh(user)
        assert verify_password("newpassword456", user.hashed_password)
        assert not verify_password("password123", user.hashed_password)
