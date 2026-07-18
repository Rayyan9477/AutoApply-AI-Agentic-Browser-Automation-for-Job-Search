"""User settings API routes with per-user database persistence."""

import structlog
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_tenant_db
from app.config.settings import get_settings as get_app_settings
from app.models.user_settings import UserSettings
from app.schemas.settings import LLMProviderStatus, SettingsResponse, SettingsUpdate

logger = structlog.get_logger(__name__)
router = APIRouter()


async def _get_or_create_settings(db: AsyncSession, user_id: str) -> UserSettings:
    """Return the user's settings row, creating defaults if absent."""
    result = await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
    settings = result.scalar_one_or_none()
    if settings is None:
        settings = UserSettings(user_id=user_id)
        db.add(settings)
        try:
            await db.commit()
        except IntegrityError:
            # Concurrent first-write from the same user — re-fetch the winner's row.
            await db.rollback()
            settings = (
                await db.execute(select(UserSettings).where(UserSettings.user_id == user_id))
            ).scalar_one()
        else:
            await db.refresh(settings)
            logger.info("settings_created_defaults", user_id=user_id)
    return settings


@router.get("/", response_model=SettingsResponse, summary="Get current settings")
async def get_settings(
    user: CurrentUser,
    db: AsyncSession = Depends(get_tenant_db),
) -> SettingsResponse:
    """Get the current user's settings from the database."""
    settings = await _get_or_create_settings(db, user.id)
    return SettingsResponse.model_validate(settings)


@router.put("/", response_model=SettingsResponse, summary="Update settings")
async def update_settings(
    update: SettingsUpdate,
    user: CurrentUser,
    db: AsyncSession = Depends(get_tenant_db),
) -> SettingsResponse:
    """Update the current user's settings. Only provided fields are changed."""
    settings = await _get_or_create_settings(db, user.id)

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)

    await db.commit()
    await db.refresh(settings)

    logger.info("settings_updated", user_id=user.id, changed_fields=list(update_data.keys()))
    return SettingsResponse.model_validate(settings)


@router.get(
    "/llm-providers",
    response_model=list[LLMProviderStatus],
    summary="List LLM provider statuses",
)
async def list_llm_providers() -> list[LLMProviderStatus]:
    """List configured LLM providers and their real configuration status."""
    settings = get_app_settings()
    llm = settings.llm

    providers_config = [
        ("openai", llm.openai_api_key, "gpt-4o"),
        ("groq", llm.groq_api_key, "llama-3.1-70b-versatile"),
        ("gemini", llm.gemini_api_key, "gemini-pro"),
        ("openrouter", llm.openrouter_api_key, llm.default_model),
        ("deepseek", llm.deepseek_api_key, "deepseek-chat"),
        ("github", llm.github_token, "gpt-4o"),
    ]

    return [
        LLMProviderStatus(
            provider=name,
            configured=bool(key.get_secret_value()),
            model=model,
            is_primary=llm.preferred_provider == name,
        )
        for name, key, model in providers_config
    ]
