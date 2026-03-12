"""User settings API routes with database persistence."""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.user_settings import UserSettings
from app.schemas.settings import LLMProviderStatus, SettingsResponse, SettingsUpdate

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _get_or_create_settings(db: AsyncSession) -> UserSettings:
    """Return the singleton UserSettings row, creating it if absent."""
    result = await db.execute(
        select(UserSettings).where(UserSettings.id == "singleton")
    )
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(id="singleton")
        db.add(settings)
        await db.commit()
        await db.refresh(settings)
        logger.info("settings_created_defaults")
    return settings


@router.get(
    "/",
    response_model=SettingsResponse,
    summary="Get current settings",
)
async def get_settings(
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Get the current user settings from the database."""
    settings = await _get_or_create_settings(db)
    return SettingsResponse.model_validate(settings)


@router.put(
    "/",
    response_model=SettingsResponse,
    summary="Update settings",
)
async def update_settings(
    update: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
) -> SettingsResponse:
    """Update user settings. Only provided fields are changed."""
    settings = await _get_or_create_settings(db)

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)

    logger.info("settings_updated", changed_fields=list(update_data.keys()))
    return SettingsResponse.model_validate(settings)


@router.get(
    "/llm-providers",
    response_model=list[LLMProviderStatus],
    summary="List LLM provider statuses",
)
async def list_llm_providers() -> list[LLMProviderStatus]:
    """List configured LLM providers and their status.

    Placeholder: returns unconfigured providers until Phase 5.
    """
    return [
        LLMProviderStatus(provider="openai", configured=False, model="gpt-4o"),
        LLMProviderStatus(provider="anthropic", configured=False, model="claude-3-opus"),
        LLMProviderStatus(provider="gemini", configured=False, model="gemini-pro"),
    ]
