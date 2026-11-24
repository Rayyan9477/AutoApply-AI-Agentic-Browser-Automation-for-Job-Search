"""Secrets provider factory. The Fernet envelope provider (``SECRETS__PROVIDER=local``,
keys via ``SECRETS__APP_KEYS``) is the shipped default; ``kms`` selects an unimplemented
AWS KMS stub."""

from __future__ import annotations

from functools import lru_cache

from cryptography.fernet import Fernet

from app.config.settings import Environment, get_settings
from app.core.secrets.base import SecretsProvider
from app.core.secrets.local import LocalSecretsProvider


@lru_cache(maxsize=1)
def get_secrets_provider() -> SecretsProvider:
    """Return the configured secrets provider (process-cached)."""
    settings = get_settings()
    cfg = settings.secrets
    if cfg.provider == "local":
        keys = [k.strip() for k in cfg.app_keys.split(",") if k.strip()]
        if not keys:
            if settings.environment == Environment.PRODUCTION:
                raise ValueError("SECRETS__APP_KEYS must be set in production")
            # Ephemeral dev key: fine for single-process local/test use.
            keys = [Fernet.generate_key().decode()]
        return LocalSecretsProvider(keys)
    if cfg.provider == "kms":
        from app.core.secrets.kms import KmsSecretsProvider

        return KmsSecretsProvider()
    raise ValueError(f"Unknown secrets provider: {cfg.provider}")
