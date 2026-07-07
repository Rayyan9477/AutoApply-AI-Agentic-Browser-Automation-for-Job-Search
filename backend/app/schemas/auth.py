"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, ConfigDict, Field


class RegisterRequest(BaseModel):
    """New-account registration payload."""

    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = None


class TokenResponse(BaseModel):
    """Access-token response (refresh token is set as an httpOnly cookie)."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Public view of a user account."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str | None = None
    is_active: bool


class WSTicketResponse(BaseModel):
    """Short-lived ticket for authenticating a WebSocket handshake."""

    ticket: str
