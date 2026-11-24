"""Glassdoor job platform integration using browser-use Agent.

Implements the ``JobPlatform`` interface for Glassdoor, handling login,
job search, detail scraping, and application submission.
"""

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

# Glassdoor-specific URLs
GLASSDOOR_JOBS_URL = "https://www.glassdoor.com/Job/jobs.htm"
GLASSDOOR_LOGIN_URL = "https://www.glassdoor.com/profile/login_input.htm"


class GlassdoorPlatform(JobPlatform):
    """Glassdoor job platform integration.

    Uses browser-use Agent to navigate Glassdoor's web interface for
    authentication, job search, and application submission.
    """

    @property
    def name(self) -> str:
        """Return the platform identifier."""
        return "glassdoor"

    async def login(self, credentials: dict[str, str]) -> bool:
        """Login to Glassdoor using browser-use Agent.

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
                "glassdoor",
                "No credentials provided. Import a saved session via the "
                "platform-sessions API or provide email/password.",
            )

        agent = BrowserAgent(
            task=(
                f"Go to {GLASSDOOR_LOGIN_URL} and log in with the provided "
                "credentials. Enter the email address and password, then "
                "click the Sign In button. "
                "After login, verify you're on the Glassdoor home page."
            ),
            sensitive_data={
                "x_username": credentials["email"],
                "x_password": credentials["password"],
            },
        )
        try:
            await agent.run()
            logger.info("glassdoor.login_success")
            return True
        except Exception as exc:
            logger.error("glassdoor.login_failed", error=str(exc))
            raise AuthenticationError("glassdoor", str(exc)) from exc
        finally:
            await agent.close()

    async def search(
        self,
        query: str,
        location: str = "",
        filters: dict[str, Any] | None = None,
        user_id: str | None = None,
    ) -> list[JobListing]:
        """Search Glassdoor for jobs matching the query.

        Args:
            query: Job search keywords (e.g. "Product Manager").
            location: Geographic filter (e.g. "Austin, TX").
            filters: Optional Glassdoor-specific filters (date_posted,
                salary, company_rating, job_type, remote).

        Returns:
            List of ``JobListing`` objects from search results.

        Raises:
            SearchError: If the search fails.
        """
        search_url = f"{GLASSDOOR_JOBS_URL}?sc.keyword={query}"
        if location:
            search_url += f"&locT=C&locKeyword={location}"

        filter_instructions = self._build_filter_instructions(filters)

        task = (
            f"Navigate to {search_url}. "
            f"{filter_instructions}"
            "Extract the first 20 job listings visible on the page. "
            "For each job, extract: the job title, company name, location, "
            "the direct job URL, company rating if shown, salary estimate "
            "if shown, and whether it mentions remote work. "
            "Return the results as a JSON array of objects with keys: "
            "id, title, company, location, url, rating, salary, remote."
        )

        agent = BrowserAgent(task=task, user_id=user_id)
        try:
            result = await agent.run()
            listings = self._parse_search_results(result, query)
            logger.info(
                "glassdoor.search_complete",
                query=query,
                count=len(listings),
            )
            return listings
        except Exception as exc:
            logger.error(
                "glassdoor.search_failed",
                query=query,
                error=str(exc),
            )
            raise SearchError("glassdoor", str(exc)) from exc
        finally:
            await agent.close()

    async def scrape_details(self, job_url: str) -> JobListing | None:
        """Scrape full job details from a Glassdoor job page.

        Args:
            job_url: Direct URL to the Glassdoor job posting.

        Returns:
            ``JobListing`` with full details, or ``None`` on failure.
        """
        task = (
            f"Navigate to {job_url}. Extract the full job posting details: "
            "job title, company name, location, full job description text, "
            "required qualifications and skills, salary estimate if shown, "
            "job type (full-time/part-time/contract), company rating, and "
            "whether it's remote. Return the data as a JSON object with "
            "keys: id, title, company, location, description, skills, "
            "salary_min, salary_max, job_type, remote."
        )
        agent = BrowserAgent(task=task)
        try:
            result = await agent.run()
            return self._parse_job_details(result, job_url)
        except Exception as exc:
            logger.warning(
                "glassdoor.scrape_failed",
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
        """Apply to a Glassdoor job posting.

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
            "Click the 'Apply' or 'Easy Apply' button if available. "
            "If it redirects to the company website, follow the link "
            "and complete the application there. "
            "Fill out the application form step by step. "
            f"Upload the resume from '{resume_path}'. "
        )
        if cover_letter_path:
            task += f"Upload the cover letter from '{cover_letter_path}'. "
        task += (
            "Complete all required fields in the application form. "
            "Review and submit the application. "
            "Confirm the submission was successful."
        )

        agent = BrowserAgent(task=task)
        try:
            await agent.run()
            logger.info(
                "glassdoor.apply_success",
                job_id=job.platform_job_id,
            )
            return True
        except Exception as exc:
            logger.error(
                "glassdoor.apply_failed",
                job_id=job.platform_job_id,
                error=str(exc),
            )
            raise ApplicationSubmissionError("glassdoor", str(exc)) from exc
        finally:
            await agent.close()

    def _build_filter_instructions(
        self,
        filters: dict[str, Any] | None,
    ) -> str:
        """Build agent task instructions from search filters.

        Args:
            filters: Optional dict of Glassdoor filter parameters.

        Returns:
            Instruction string to append to the search task.
        """
        if not filters:
            return ""

        parts: list[str] = []
        if "date_posted" in filters:
            parts.append(f"Filter by date posted: {filters['date_posted']}. ")
        if "salary" in filters:
            parts.append(f"Filter by salary range: {filters['salary']}. ")
        if "company_rating" in filters:
            parts.append(f"Filter by minimum company rating: " f"{filters['company_rating']}. ")
        if "job_type" in filters:
            parts.append(f"Filter by job type: {filters['job_type']}. ")
        if filters.get("remote"):
            parts.append("Filter for remote positions only. ")
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
                        platform="glassdoor",
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
                platform="glassdoor",
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
