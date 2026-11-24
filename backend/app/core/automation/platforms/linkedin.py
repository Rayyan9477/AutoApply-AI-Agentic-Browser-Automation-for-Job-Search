"""LinkedIn job platform integration using browser-use Agent.

Implements the ``JobPlatform`` interface for LinkedIn, handling login,
job search, detail scraping, and Easy Apply submission.
"""

from __future__ import annotations

from typing import Any

import structlog

from app.core.automation.agent import BrowserAgent
from app.core.automation.platforms.base import (
    JobListing,
    JobPlatform,
    coerce_agent_dict,
    coerce_agent_list,
)
from app.core.exceptions import (
    ApplicationSubmissionError,
    AuthenticationError,
    SearchError,
)

logger = structlog.get_logger(__name__)

# LinkedIn-specific URLs
LINKEDIN_JOBS_URL = "https://www.linkedin.com/jobs/search/"
LINKEDIN_LOGIN_URL = "https://www.linkedin.com/login"


class LinkedInPlatform(JobPlatform):
    """LinkedIn job platform integration.

    Uses browser-use Agent to navigate LinkedIn's web interface for
    authentication, job search, and application submission via Easy Apply.
    """

    @property
    def name(self) -> str:
        """Return the platform identifier."""
        return "linkedin"

    async def login(self, credentials: dict[str, str]) -> bool:
        """Login to LinkedIn using browser-use Agent.

        Session persistence is handled by the encrypted CredentialStore via
        the platform-sessions API (see ``app/core/secrets/credential_store.py``);
        this method performs a fresh credential-based login and never writes
        session state to disk.

        Args:
            credentials: Dict with ``email`` and ``password`` keys.

        Returns:
            ``True`` if the agent-driven login succeeded.

        Raises:
            AuthenticationError: If login fails or credentials are missing.
        """
        if not credentials.get("email") or not credentials.get("password"):
            raise AuthenticationError(
                "linkedin",
                "No credentials provided. Import a saved session via the "
                "platform-sessions API or provide email/password.",
            )

        agent = BrowserAgent(
            task=(
                f"Go to {LINKEDIN_LOGIN_URL} and log in with the provided "
                "credentials. Enter the username in the email field and the "
                "password in the password field, then click Sign In. "
                "After login, verify you're on the LinkedIn feed page."
            ),
            sensitive_data={
                "x_username": credentials["email"],
                "x_password": credentials["password"],
            },
        )
        try:
            await agent.run()
            logger.info("linkedin.login_success")
            return True
        except Exception as exc:
            logger.error("linkedin.login_failed", error=str(exc))
            raise AuthenticationError("linkedin", str(exc)) from exc
        finally:
            await agent.close()

    async def search(
        self,
        query: str,
        location: str = "",
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> list[JobListing]:
        """Search LinkedIn for jobs matching the query.

        Args:
            query: Job search keywords (e.g. "Software Engineer").
            location: Geographic filter (e.g. "San Francisco, CA").
            filters: Optional LinkedIn-specific filters (date_posted,
                experience_level, remote, job_type).

        Returns:
            List of ``JobListing`` objects from search results.

        Raises:
            SearchError: If the search fails.
        """
        search_url = f"{LINKEDIN_JOBS_URL}?keywords={query}"
        if location:
            search_url += f"&location={location}"

        filter_instructions = self._build_filter_instructions(filters)

        task = (
            f"Navigate to {search_url}. "
            f"{filter_instructions}"
            "Extract the first 20 job listings visible on the page. "
            "For each job, extract: the job title, company name, location, "
            "the direct job URL, and whether it mentions remote work. "
            "Return the results as a JSON array of objects with keys: "
            "id, title, company, location, url, remote."
        )

        agent = BrowserAgent(task=task, user_id=user_id)
        try:
            result = await agent.run()
            listings = self._parse_search_results(result, query)
            logger.info(
                "linkedin.search_complete",
                query=query,
                count=len(listings),
            )
            return listings
        except Exception as exc:
            logger.error("linkedin.search_failed", query=query, error=str(exc))
            raise SearchError("linkedin", str(exc)) from exc
        finally:
            await agent.close()

    async def scrape_details(self, job_url: str) -> JobListing | None:
        """Scrape full job details from a LinkedIn job page.

        Args:
            job_url: Direct URL to the LinkedIn job posting.

        Returns:
            ``JobListing`` with full details, or ``None`` on failure.
        """
        task = (
            f"Navigate to {job_url}. Extract the full job posting details: "
            "job title, company name, location, full job description text, "
            "required skills or qualifications, salary range if displayed, "
            "job type (full-time/part-time/contract), and whether it's remote. "
            "Return the data as a JSON object with keys: id, title, company, "
            "location, description, skills, salary_min, salary_max, "
            "job_type, remote."
        )
        agent = BrowserAgent(task=task)
        try:
            result = await agent.run()
            return self._parse_job_details(result, job_url)
        except Exception as exc:
            logger.warning(
                "linkedin.scrape_failed",
                url=job_url,
                error=str(exc),
            )
            return None
        finally:
            await agent.close()

    async def apply(
        self,
        job: JobListing,
        resume_path: str,
        cover_letter_path: str | None = None,
    ) -> bool:
        """Apply to a LinkedIn job using Easy Apply.

        Args:
            job: The target job listing.
            resume_path: Absolute path to the resume file.
            cover_letter_path: Optional path to the cover letter file.

        Returns:
            ``True`` if the application was submitted successfully.

        Raises:
            ApplicationSubmissionError: If application submission fails.
        """
        task = (
            f"Navigate to {job.url}. "
            "Click the 'Easy Apply' button if available. "
            "Fill out the application form step by step. "
            f"Upload the resume from '{resume_path}'. "
        )
        if cover_letter_path:
            task += f"Upload the cover letter from '{cover_letter_path}'. "
        task += (
            "Complete all required fields in the application. "
            "Review and submit the application. "
            "Confirm the submission was successful."
        )

        agent = BrowserAgent(task=task)
        try:
            await agent.run()
            logger.info(
                "linkedin.apply_success",
                job_id=job.platform_job_id,
            )
            return True
        except Exception as exc:
            logger.error(
                "linkedin.apply_failed",
                job_id=job.platform_job_id,
                error=str(exc),
            )
            raise ApplicationSubmissionError("linkedin", str(exc)) from exc
        finally:
            await agent.close()

    def _build_filter_instructions(
        self,
        filters: dict[str, Any] | None,
    ) -> str:
        """Build agent task instructions from search filters.

        Args:
            filters: Optional dict of LinkedIn filter parameters.

        Returns:
            Instruction string to append to the search task.
        """
        if not filters:
            return ""

        parts: list[str] = []
        if "date_posted" in filters:
            parts.append(f"Filter by date posted: {filters['date_posted']}. ")
        if "experience_level" in filters:
            parts.append(f"Filter by experience level: {filters['experience_level']}. ")
        if filters.get("remote"):
            parts.append("Filter for remote positions only. ")
        if "job_type" in filters:
            parts.append(f"Filter by job type: {filters['job_type']}. ")
        return "".join(parts)

    def _parse_search_results(
        self,
        raw_result: Any,
        query: str,
    ) -> list[JobListing]:
        """Parse browser-use Agent output into JobListing models.

        Args:
            raw_result: Raw output from the browser-use Agent.
            query: Original search query for logging context.

        Returns:
            List of parsed ``JobListing`` objects.
        """
        listings: list[JobListing] = []
        for item in coerce_agent_list(raw_result):
            if isinstance(item, dict):
                listings.append(
                    JobListing(
                        platform="linkedin",
                        platform_job_id=str(item.get("id", "")),
                        title=item.get("title", ""),
                        company=item.get("company", ""),
                        location=item.get("location", ""),
                        url=item.get("url", ""),
                        remote=item.get("remote", False),
                    )
                )
        return listings

    def _parse_job_details(
        self,
        raw_result: Any,
        url: str,
    ) -> JobListing | None:
        """Parse scraped job details into a JobListing model.

        Args:
            raw_result: Raw output from the browser-use Agent.
            url: The job posting URL.

        Returns:
            ``JobListing`` with full details, or ``None`` if unparseable.
        """
        data = coerce_agent_dict(raw_result)
        if data is not None:
            return JobListing(
                platform="linkedin",
                platform_job_id=str(data.get("id", "")),
                title=data.get("title", ""),
                company=data.get("company", ""),
                location=data.get("location", ""),
                url=url,
                description=data.get("description", ""),
                skills_required=data.get("skills", []),
                salary_min=data.get("salary_min"),
                salary_max=data.get("salary_max"),
                job_type=data.get("job_type", ""),
                remote=data.get("remote", False),
            )
        return None
