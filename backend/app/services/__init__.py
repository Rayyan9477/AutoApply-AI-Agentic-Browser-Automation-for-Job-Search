"""Business logic service layer.

Modules:
    job_search  -- Job search and CRUD operations
    application -- Application lifecycle management
    resume      -- Resume upload, generation, and scoring
    analytics   -- Dashboard statistics and reporting
    queue       -- Redis-based task queue operations
"""

__all__ = [
    "analytics",
    "application",
    "job_search",
    "queue",
    "resume",
]
