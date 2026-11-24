"""Base classes for job platform integrations.

Defines the ``JobListing`` data model and the ``JobPlatform`` abstract
base class that all platform plugins (LinkedIn, Indeed, Glassdoor, etc.)
must implement.
"""

import contextlib
import json
import re
from abc import ABC, abstractmethod
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)


_FENCE_RE = re.compile(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```$", re.DOTALL)


def _loads_lenient(text: str) -> Any:
    """Decode the JSON an LLM agent returned: bare, in a code fence, or embedded in prose."""
    text = text.strip()
    fenced = _FENCE_RE.match(text)
    if fenced:
        text = fenced.group(1).strip()
    with contextlib.suppress(ValueError):
        return json.loads(text)
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char in "[{":
            with contextlib.suppress(ValueError):
                return decoder.raw_decode(text, start)[0]
    return text


def _agent_payload(raw_result: Any) -> Any:
    """Unwrap a browser-use result into its decoded payload.

    ``BrowserAgent.run`` returns ``history.final_result()`` (a ``str``); a raw
    ``AgentHistoryList`` (anything with a callable ``final_result``) is still accepted.
    """
    payload = raw_result
    final = getattr(raw_result, "final_result", None)
    if callable(final):
        payload = None
        with contextlib.suppress(Exception):
            payload = final()
    if isinstance(payload, str):
        payload = _loads_lenient(payload)
    return payload


def coerce_agent_dict(raw_result: Any) -> dict[str, Any] | None:
    """Best-effort: turn a browser-use result into the scraped object, or ``None``."""
    payload = _agent_payload(raw_result)
    return payload if isinstance(payload, dict) else None


def coerce_agent_list(raw_result: Any) -> list[Any]:
    """Best-effort: turn a browser-use result into the list of scraped items.

    Accepts the ``final_result()`` text (a JSON array, or a ``{"jobs": [...]}``-style object,
    optionally fenced or wrapped in prose) so the parsers see the array they expect instead of
    silently yielding zero listings. Returns ``[]`` when nothing list-like can be recovered.
    """
    payload = _agent_payload(raw_result)
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for value in payload.values():  # e.g. {"jobs": [...]}
            if isinstance(value, list):
                return value
    return []


class JobListing(BaseModel):
    """Normalized job listing from any platform.

    All platform integrations convert their raw data into this shared
    model so the rest of the system works with a single schema.
    """

    model_config = ConfigDict(frozen=True)

    platform: str
    platform_job_id: str
    title: str
    company: str
    location: str = ""
    url: str = ""
    description: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str = "USD"
    job_type: str = ""  # full-time, part-time, contract
    remote: bool = False
    skills_required: list[str] = Field(default_factory=list)
    skills_preferred: list[str] = Field(default_factory=list)
    posted_at: str = ""
    raw_data: dict[str, Any] = Field(default_factory=dict)


class JobPlatform(ABC):
    """Abstract base class for job platform integrations.

    Each supported job board (LinkedIn, Indeed, Glassdoor, etc.)
    implements this interface. Platform instances are created and
    managed through the ``PlatformRegistry``.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique platform identifier (e.g. ``linkedin``, ``indeed``)."""
        ...

    @abstractmethod
    async def login(self, credentials: dict[str, str]) -> bool:
        """Authenticate with the platform.

        Args:
            credentials: Platform-specific credential mapping
                         (e.g. ``{"email": "...", "password": "..."}``).

        Returns:
            ``True`` if login succeeded, ``False`` otherwise.
        """
        ...

    @abstractmethod
    async def search(
        self,
        query: str,
        location: str = "",
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> list[JobListing]:
        """Search for job listings matching the given criteria.

        Args:
            query: Job search query string.
            location: Geographic filter (city, state, or "remote").
            filters: Platform-specific filter parameters.
            user_id: Owner of the search; the agent run is budget-checked and billed to them.

        Returns:
            List of normalized ``JobListing`` objects.
        """
        ...

    @abstractmethod
    async def scrape_details(self, job_url: str) -> JobListing | None:
        """Scrape full details for a single job listing.

        Args:
            job_url: Direct URL to the job posting.

        Returns:
            ``JobListing`` with full description, or ``None`` if not found.
        """
        ...

    @abstractmethod
    async def apply(
        self,
        job: JobListing,
        resume_path: str,
        cover_letter_path: str | None = None,
    ) -> bool:
        """Submit a job application through the platform.

        Args:
            job: The target job listing.
            resume_path: Path to the resume file to upload.
            cover_letter_path: Optional path to the cover letter file.

        Returns:
            ``True`` if the application was submitted successfully.
        """
        ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} platform={self.name!r}>"
