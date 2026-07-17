"""Authentication routes: register, login, refresh, logout, current user, WS ticket."""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError as DBIntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db
from app.config.settings import Environment, get_settings
from app.core.exceptions import AuthError, IntegrityError
from app.core.ratelimit import rate_limit
from app.core.security import (
    create_access_token,
    create_ws_ticket,
    generate_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.base import generate_uuid
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import (
    ForgotPasswordRequest,
    MessageResponse,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserResponse,
    WSTicketResponse,
)
from app.services import password_reset as password_reset_service

logger = structlog.get_logger(__name__)
router = APIRouter()

_REFRESH_COOKIE = "refresh_token"
_REFRESH_PATH = "/api/v1/auth"
_AUTH_RATE = Depends(rate_limit(5, 60))  # 5 attempts / minute on auth endpoints


def _set_refresh_cookie(response: Response, raw_refresh: str) -> None:
    auth = get_settings().auth
    response.set_cookie(
        _REFRESH_COOKIE,
        raw_refresh,
        httponly=True,
        # Secure everywhere except local DEVELOPMENT so STAGING (often HTTP-fronted) does
        # not transmit the long-lived refresh cookie in cleartext.
        secure=get_settings().environment != Environment.DEVELOPMENT,
        samesite="strict",
        path=_REFRESH_PATH,
        max_age=auth.refresh_token_expire_days * 86400,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(_REFRESH_COOKIE, path=_REFRESH_PATH)


async def _issue_session(
    db: AsyncSession, user: User, response: Response, *, family_id: str | None = None
) -> str:
    """Mint an access token and a rotating refresh token (set as an httpOnly cookie).

    A new ``family_id`` starts a fresh token family; passing an existing one continues
    the family across a rotation (so reuse of a retired token can revoke the whole line).
    """
    auth = get_settings().auth
    raw_refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=family_id or generate_uuid(),
            expires_at=datetime.now(UTC) + timedelta(days=auth.refresh_token_expire_days),
        )
    )
    await db.commit()
    _set_refresh_cookie(response, raw_refresh)
    return create_access_token(user.id)


@router.post("/register", response_model=UserResponse, status_code=201, dependencies=[_AUTH_RATE])
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    """Create a new user account."""
    existing = (await db.execute(select(User).where(User.email == data.email))).scalar_one_or_none()
    if existing is not None:
        raise IntegrityError("Email already registered")
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    try:
        await db.commit()
    except DBIntegrityError as exc:
        # Two concurrent registrations for the same email both pass the check above; the loser's
        # unique-constraint violation becomes a clean 409 rather than an uncaught 500.
        await db.rollback()
        raise IntegrityError("Email already registered") from exc
    await db.refresh(user)
    logger.info("user_registered", user_id=user.id)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=TokenResponse, dependencies=[_AUTH_RATE])
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[AsyncSession, Depends(get_db)],
    response: Response,
) -> TokenResponse:
    """Authenticate (OAuth2 password flow) and return an access token."""
    user = (await db.execute(select(User).where(User.email == form.username))).scalar_one_or_none()
    # Always run the (slow) Argon2 verification — against DUMMY_HASH when the email is
    # unknown — so the response time does not reveal whether an account exists.
    pw_ok = verify_password(form.password, user.hashed_password if user else None)
    if user is None or not pw_ok or not user.is_active or user.deleted_at is not None:
        raise AuthError("Invalid credentials")

    access = await _issue_session(db, user, response)
    logger.info("user_login", user_id=user.id)
    return TokenResponse(access_token=access)


@router.post("/forgot-password", response_model=MessageResponse, dependencies=[_AUTH_RATE])
async def forgot_password(
    data: ForgotPasswordRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Email a password-reset link if the address maps to an active account.

    Always returns the same body regardless of whether the email exists, so it can't be used
    to enumerate accounts.
    """
    await password_reset_service.request_password_reset(db, data.email)
    return MessageResponse(
        message="If that email is registered, a password-reset link is on its way."
    )


@router.post("/reset-password", response_model=MessageResponse, dependencies=[_AUTH_RATE])
async def reset_password(
    data: ResetPasswordRequest,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> MessageResponse:
    """Redeem a reset token, set the new password, and revoke all existing sessions."""
    await password_reset_service.reset_password(db, data.token, data.password)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Your password has been reset. Please sign in.")


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TokenResponse:
    """Rotate the refresh token and issue a new access token.

    Single-use with reuse-detection: presenting an already-used or revoked token revokes
    the entire token family (a stolen-token breach response).
    """
    raw = request.cookies.get(_REFRESH_COOKIE)
    if not raw:
        raise AuthError("Missing refresh token")

    row = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
    ).scalar_one_or_none()
    if row is None:
        raise AuthError("Invalid refresh token")

    expires = row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=UTC)
    if expires < datetime.now(UTC):
        raise AuthError("Refresh token expired")

    # Atomically claim the token (used False -> True). This single conditional UPDATE
    # closes the check-then-set TOCTOU race: only one of two concurrent refreshes presenting
    # the same token can succeed; a rowcount of 0 means it was already used/revoked (a replay
    # or the lost side of the race) -> reuse-detection revokes the whole family.
    claim = await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.id == row.id,
            RefreshToken.used.is_(False),
            RefreshToken.revoked.is_(False),
        )
        .values(used=True)
    )
    if claim.rowcount == 0:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == row.family_id)
            .values(revoked=True)
        )
        await db.commit()
        _clear_refresh_cookie(response)
        logger.warning("refresh_token_reuse_detected", user_id=row.user_id, family=row.family_id)
        raise AuthError("Refresh token reuse detected")

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active or user.deleted_at is not None:
        raise AuthError("Invalid or inactive user")

    access = await _issue_session(db, user, response, family_id=row.family_id)
    return TokenResponse(access_token=access)


@router.post("/logout", status_code=204)
async def logout(
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Revoke the current refresh-token family and clear the cookie."""
    raw = request.cookies.get(_REFRESH_COOKIE)
    if raw:
        row = (
            await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw)))
        ).scalar_one_or_none()
        if row is not None:
            await db.execute(
                update(RefreshToken)
                .where(RefreshToken.family_id == row.family_id)
                .values(revoked=True)
            )
            await db.commit()
    _clear_refresh_cookie(response)


@router.delete("/account", status_code=204)
async def delete_account(
    user: CurrentUser,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Soft-delete the current account (D9): hidden immediately, hard-purged after the grace
    period by the scheduled worker. Revokes all refresh tokens and clears the cookie."""
    db_user = await db.get(User, user.id)
    if db_user is not None and db_user.deleted_at is None:
        db_user.deleted_at = datetime.now(UTC)
        await db.execute(
            update(RefreshToken).where(RefreshToken.user_id == user.id).values(revoked=True)
        )
        await db.commit()
        logger.info("account_soft_deleted", user_id=user.id)
    _clear_refresh_cookie(response)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    """Return the authenticated user."""
    return UserResponse.model_validate(user)


@router.get("/ws-ticket", response_model=WSTicketResponse)
async def ws_ticket(user: CurrentUser) -> WSTicketResponse:
    """Issue a short-lived ticket for authenticating a WebSocket connection."""
    return WSTicketResponse(ticket=create_ws_ticket(user.id))
