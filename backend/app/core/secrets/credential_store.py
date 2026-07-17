"""Per-user encrypted credential storage.

Stores BYO LLM keys (``kind=llm_key``) and platform browser session state
(``kind=platform_cookies`` — an encrypted ``storage_state`` from an assisted login, D7).
``user_id`` is always passed explicitly — ``UserCredential`` is intentionally not a
``TenantMixin`` entity (reads may run outside a tenant context, e.g. in the worker).
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.secrets.base import EncryptedBlob, SecretsProvider
from app.core.secrets.factory import get_secrets_provider
from app.models.user_credential import UserCredential

_KIND_LLM_KEY = "llm_key"
_KIND_COOKIES = "platform_cookies"


class CredentialStore:
    """Reads and writes envelope-encrypted credentials for a user."""

    def __init__(self, provider: SecretsProvider | None = None) -> None:
        self._provider = provider or get_secrets_provider()

    async def _put(
        self, db: AsyncSession, user_id: str, kind: str, provider: str, plaintext: bytes
    ) -> None:
        context = {"user_id": user_id, "kind": kind, "provider": provider}
        blob = await self._provider.encrypt(plaintext, context=context)
        existing = (
            await db.execute(
                select(UserCredential).where(
                    UserCredential.user_id == user_id,
                    UserCredential.kind == kind,
                    UserCredential.provider == provider,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                UserCredential(
                    user_id=user_id,
                    kind=kind,
                    provider=provider,
                    blob=blob.model_dump(),
                    kek_id=blob.kek_id,
                )
            )
        else:
            existing.blob = blob.model_dump()
            existing.kek_id = blob.kek_id
        await db.commit()

    async def _get(
        self, db: AsyncSession, user_id: str, kind: str, provider: str
    ) -> bytes | None:
        row = (
            await db.execute(
                select(UserCredential).where(
                    UserCredential.user_id == user_id,
                    UserCredential.kind == kind,
                    UserCredential.provider == provider,
                )
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        context = {"user_id": user_id, "kind": kind, "provider": provider}
        return await self._provider.decrypt(EncryptedBlob(**row.blob), context=context)

    async def put_llm_key(
        self, db: AsyncSession, user_id: str, provider_name: str, api_key: str
    ) -> None:
        """Encrypt and upsert a user's BYO LLM provider key."""
        await self._put(db, user_id, _KIND_LLM_KEY, provider_name, api_key.encode())

    async def get_llm_key(
        self, db: AsyncSession, user_id: str, provider_name: str
    ) -> str | None:
        """Return a user's decrypted LLM provider key, or ``None`` if not set."""
        data = await self._get(db, user_id, _KIND_LLM_KEY, provider_name)
        return data.decode() if data is not None else None

    async def save_session_cookies(
        self, db: AsyncSession, user_id: str, platform: str, storage_state: dict[str, Any]
    ) -> None:
        """Encrypt and upsert a platform's browser ``storage_state`` (assisted-login session)."""
        await self._put(db, user_id, _KIND_COOKIES, platform, json.dumps(storage_state).encode())

    async def load_session_cookies(
        self, db: AsyncSession, user_id: str, platform: str
    ) -> dict[str, Any] | None:
        """Return a platform's decrypted browser ``storage_state``, or ``None`` if not set."""
        data = await self._get(db, user_id, _KIND_COOKIES, platform)
        return json.loads(data.decode()) if data is not None else None

    async def delete_session_cookies(
        self, db: AsyncSession, user_id: str, platform: str
    ) -> bool:
        """Delete a platform's stored session cookies. Returns True if a row was removed."""
        result = await db.execute(
            delete(UserCredential).where(
                UserCredential.user_id == user_id,
                UserCredential.kind == _KIND_COOKIES,
                UserCredential.provider == platform,
            )
        )
        await db.commit()
        return result.rowcount > 0

    async def rotate_all(self, db: AsyncSession) -> int:
        """Re-wrap every stored credential under the provider's CURRENT KEK.

        Run after prepending a new key to ``SECRETS__APP_KEYS`` (MultiFernet still decrypts
        old blobs; this re-encrypts them to the new KEK). Skips rows already on the current
        KEK. Returns the number of rows rotated. Runs UNSCOPED (all tenants) — an admin op.
        """
        current = self._provider.current_kek_id
        rows = (await db.execute(select(UserCredential))).scalars().all()
        rotated = 0
        for row in rows:
            if row.kek_id == current:
                continue
            context = {"user_id": row.user_id, "kind": row.kind, "provider": row.provider}
            new_blob = await self._provider.rotate(EncryptedBlob(**row.blob), context=context)
            row.blob = new_blob.model_dump()
            row.kek_id = new_blob.kek_id
            rotated += 1
        if rotated:
            await db.commit()
        return rotated
