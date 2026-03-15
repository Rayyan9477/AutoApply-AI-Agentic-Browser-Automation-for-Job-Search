"""Pydantic schemas for user settings API requests and responses."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SettingsResponse(BaseModel):
    """Current user settings."""

    model_config = ConfigDict(from_attributes=True)

    apply_mode: str = "review"
    min_ats_score: float = 0.75
    max_parallel: int = 3
    preferred_provider: str = "openai"
    platforms_enabled: list[str] = Field(
        default_factory=lambda: ["linkedin", "indeed", "glassdoor"],
    )
    candidate_profile: dict[str, Any] = Field(default_factory=dict)

    @field_validator("candidate_profile", mode="before")
    @classmethod
    def _none_to_empty_dict(cls, v: Any) -> dict[str, Any]:
        if v is None:
            return {}
        return v


class SettingsUpdate(BaseModel):
    """Request to update user settings."""

    apply_mode: str | None = None
    min_ats_score: float | None = Field(default=None, ge=0.0, le=1.0)
    max_parallel: int | None = Field(default=None, ge=1, le=5)
    preferred_provider: str | None = None
    platforms_enabled: list[str] | None = None
    candidate_profile: dict[str, Any] | None = None


class LLMProviderStatus(BaseModel):
    """Status of a configured LLM provider."""

    provider: str
    configured: bool = False
    model: str = ""
    is_primary: bool = False
