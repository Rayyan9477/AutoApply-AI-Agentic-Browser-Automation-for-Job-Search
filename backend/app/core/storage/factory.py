"""Storage backend factory (local now; S3 deferred to Phase 4)."""

from __future__ import annotations

from functools import lru_cache

from app.config.settings import get_settings
from app.core.storage.base import FileStorage
from app.core.storage.local import LocalFileStorage


@lru_cache(maxsize=1)
def get_storage() -> FileStorage:
    """Return the configured storage backend (process-cached)."""
    cfg = get_settings().storage
    if cfg.provider == "local":
        return LocalFileStorage(cfg.local_root, cfg.url_signing_secret.get_secret_value())
    if cfg.provider == "s3":
        from app.core.storage.s3 import S3FileStorage

        return S3FileStorage(
            bucket=cfg.bucket,
            # R2 expects region "auto"; default it when a custom endpoint is set.
            region=cfg.region or ("auto" if cfg.endpoint_url else None),
            endpoint_url=cfg.endpoint_url or None,
            access_key_id=cfg.access_key_id.get_secret_value() or None,
            secret_access_key=cfg.secret_access_key.get_secret_value() or None,
        )
    raise ValueError(f"Unknown storage provider: {cfg.provider}")
