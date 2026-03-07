"""Browser session persistence for platform logins.

Manages per-platform cookie storage so that browser sessions can be
restored across agent invocations without re-authenticating.
"""

import json
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

SESSION_DIR = Path("data/sessions")


class SessionManager:
    """Manages browser session cookies per platform.

    Cookies are stored as JSON files under
    ``<session_dir>/<platform>/cookies.json``.

    Args:
        session_dir: Root directory for session storage.
            Defaults to ``data/sessions``.
    """

    def __init__(self, session_dir: Path = SESSION_DIR) -> None:
        """Initialize the session manager.

        Args:
            session_dir: Root directory for session storage.
        """
        self._session_dir = session_dir
        self._session_dir.mkdir(parents=True, exist_ok=True)

    def _cookie_path(self, platform: str) -> Path:
        """Return the cookie file path for a given platform.

        Args:
            platform: Platform identifier (e.g. ``linkedin``).

        Returns:
            Path to the platform's cookie JSON file.
        """
        return self._session_dir / platform / "cookies.json"

    async def save_cookies(
        self,
        platform: str,
        cookies: list[dict[str, Any]],
    ) -> None:
        """Save browser cookies for a platform.

        Args:
            platform: Platform identifier.
            cookies: List of cookie dicts from the browser context.
        """
        path = self._cookie_path(platform)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cookies, indent=2))
        logger.info(
            "session.cookies_saved",
            platform=platform,
            count=len(cookies),
        )

    async def load_cookies(
        self,
        platform: str,
    ) -> list[dict[str, Any]] | None:
        """Load saved cookies for a platform.

        Args:
            platform: Platform identifier.

        Returns:
            List of cookie dicts, or ``None`` if no session exists
            or the file is corrupt.
        """
        path = self._cookie_path(platform)
        if not path.exists():
            return None
        try:
            cookies: list[dict[str, Any]] = json.loads(path.read_text())
            logger.info(
                "session.cookies_loaded",
                platform=platform,
                count=len(cookies),
            )
            return cookies
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning(
                "session.cookies_load_failed",
                platform=platform,
                error=str(exc),
            )
            return None

    async def clear_session(self, platform: str) -> None:
        """Clear saved session for a platform.

        Args:
            platform: Platform identifier.
        """
        path = self._cookie_path(platform)
        if path.exists():
            path.unlink()
            logger.info("session.cleared", platform=platform)

    async def has_session(self, platform: str) -> bool:
        """Check if a saved session exists for a platform.

        Args:
            platform: Platform identifier.

        Returns:
            ``True`` if a cookie file exists on disk.
        """
        return self._cookie_path(platform).exists()
