"""Job platform integrations with auto-registration.

Importing this package registers all built-in platform plugins
(LinkedIn, Indeed, Glassdoor) with the global ``platform_registry``.
"""

from app.core.automation.platforms.base import JobListing, JobPlatform
from app.core.automation.platforms.glassdoor import GlassdoorPlatform
from app.core.automation.platforms.indeed import IndeedPlatform
from app.core.automation.platforms.linkedin import LinkedInPlatform
from app.core.automation.platforms.registry import PlatformRegistry, platform_registry

# Auto-register all built-in platforms
platform_registry.register("linkedin", LinkedInPlatform)
platform_registry.register("indeed", IndeedPlatform)
platform_registry.register("glassdoor", GlassdoorPlatform)

__all__ = [
    "GlassdoorPlatform",
    "IndeedPlatform",
    "JobListing",
    "JobPlatform",
    "LinkedInPlatform",
    "PlatformRegistry",
    "platform_registry",
]
