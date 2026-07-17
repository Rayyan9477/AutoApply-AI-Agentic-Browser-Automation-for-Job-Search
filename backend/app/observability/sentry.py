"""Optional Sentry error tracking. No-op unless SENTRY_DSN is configured."""

from __future__ import annotations

import structlog

from app.config.settings import get_settings

logger = structlog.get_logger(__name__)

_initialized = False


def init_sentry(component: str) -> bool:
    """Initialize Sentry for a process (API or worker). Returns True if enabled.

    Safe to call when SENTRY_DSN is unset (no-op) or the SDK is not installed. Idempotent.
    """
    global _initialized
    if _initialized:
        return True

    settings = get_settings()
    dsn = settings.sentry_dsn.get_secret_value()
    if not dsn:
        return False

    try:
        import sentry_sdk
    except ImportError:  # pragma: no cover - sentry-sdk is a declared dep
        logger.warning("sentry_sdk_not_installed")
        return False

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment.value,
        release=None,
        traces_sample_rate=0.0,  # error tracking only by default; opt into tracing later
        send_default_pii=False,
    )
    sentry_sdk.set_tag("component", component)
    _initialized = True
    logger.info("sentry_initialized", component=component, environment=settings.environment.value)
    return True
