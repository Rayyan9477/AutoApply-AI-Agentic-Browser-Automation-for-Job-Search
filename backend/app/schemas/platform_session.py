"""Schemas for importing and listing per-user platform browser sessions."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

from app.config.constants import SUPPORTED_PLATFORMS


class PlatformSessionImport(BaseModel):
    """A captured browser ``storage_state`` (Playwright shape) to persist for a platform."""

    platform: str
    storage_state: dict[str, Any]
    expires_at: datetime | None = None

    @field_validator("platform")
    @classmethod
    def _known_platform(cls, v: str) -> str:
        normalized = v.strip().lower()
        if normalized not in SUPPORTED_PLATFORMS:
            raise ValueError(
                f"Unsupported platform '{v}'. Supported: {', '.join(SUPPORTED_PLATFORMS)}"
            )
        return normalized

    @field_validator("storage_state")
    @classmethod
    def _has_cookies(cls, v: dict[str, Any]) -> dict[str, Any]:
        cookies = v.get("cookies")
        if not isinstance(cookies, list) or not cookies:
            raise ValueError(
                "storage_state must include a non-empty 'cookies' list (a Playwright storage_state)"
            )
        return v


class PlatformSessionResponse(BaseModel):
    """Public, cookie-free view of a stored platform session."""

    platform: str
    connected: bool = True
    last_verified_at: datetime | None = None
    expires_at: datetime | None = None
