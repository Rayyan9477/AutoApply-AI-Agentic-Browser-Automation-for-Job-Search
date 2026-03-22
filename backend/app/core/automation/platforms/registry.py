"""Platform registry for dynamic platform plugin management."""

from typing import Any

import structlog

from app.core.automation.platforms.base import JobPlatform

logger = structlog.get_logger(__name__)


class PlatformRegistry:
    """Registry for job platform plugins.

    Provides a central lookup for platform classes, allowing
    dynamic registration of new platforms at runtime.
    """

    def __init__(self) -> None:
        self._platforms: dict[str, type[JobPlatform]] = {}

    def register(self, name: str, platform_class: type[JobPlatform]) -> None:
        """Register a platform class under the given name.

        Args:
            name: Unique identifier for the platform.
            platform_class: The ``JobPlatform`` subclass to register.
        """
        if name in self._platforms:
            logger.warning(
                "platform_overwritten",
                name=name,
                old=self._platforms[name].__name__,
                new=platform_class.__name__,
            )
        self._platforms[name] = platform_class
        logger.info("platform_registered", name=name, cls=platform_class.__name__)

    def get(self, name: str) -> type[JobPlatform] | None:
        """Look up a registered platform class by name.

        Args:
            name: Platform identifier.

        Returns:
            The platform class, or ``None`` if not registered.
        """
        return self._platforms.get(name)

    def has(self, name: str) -> bool:
        """Check whether a platform is registered.

        Args:
            name: Platform identifier.

        Returns:
            ``True`` if the platform is registered.
        """
        return name in self._platforms

    def list_platforms(self) -> list[str]:
        """Return the names of all registered platforms."""
        return list(self._platforms.keys())

    def create(self, name: str, **kwargs: Any) -> JobPlatform:
        """Instantiate a registered platform.

        Args:
            name: Platform identifier.
            **kwargs: Arguments forwarded to the platform constructor.

        Returns:
            A new ``JobPlatform`` instance.

        Raises:
            KeyError: If the platform name is not registered.
        """
        platform_class = self._platforms.get(name)
        if platform_class is None:
            registered = ", ".join(self._platforms.keys()) or "(none)"
            raise KeyError(
                f"Platform '{name}' not registered. Available: {registered}"
            )
        return platform_class(**kwargs)


# Module-level singleton
platform_registry = PlatformRegistry()
