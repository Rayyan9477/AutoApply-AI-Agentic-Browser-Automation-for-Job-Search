"""
Job search manager to coordinate multiple job sources.
"""
from typing import Dict, List, Optional, Any
import asyncio
import logging
from datetime import datetime, timedelta

from .base import JobListing
from .indeed_integration import IndeedIntegration
from .glassdoor_integration import GlassdoorIntegration
from .linkedin_integration import LinkedInIntegration

logger = logging.getLogger(__name__)

class JobSearchManager:
    """Manager class to coordinate job searches across multiple sources."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the job search manager.
        
        Args:
            config: Configuration dictionary containing settings for all job sources
        """
        self.config = config
        self.job_sources = {}
        self._initialize_job_sources()

    def _initialize_job_sources(self):
        """Initialize all configured job sources."""
        # Initialize LinkedIn integration
        if self.config.get('job_sources', {}).get('linkedin', {}).get('enabled', False):
            try:
                self.job_sources['linkedin'] = LinkedInIntegration(
                    self.config['job_sources']['linkedin']
                )
                logger.info("LinkedIn integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize LinkedIn integration: {str(e)}")

        # Initialize Indeed integration
        if self.config.get('job_sources', {}).get('indeed', {}).get('enabled', False):
            try:
                self.job_sources['indeed'] = IndeedIntegration(
                    self.config['job_sources']['indeed']
                )
                logger.info("Indeed integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Indeed integration: {str(e)}")

        # Initialize Glassdoor integration
        if self.config.get('job_sources', {}).get('glassdoor', {}).get('enabled', False):
            try:
                self.job_sources['glassdoor'] = GlassdoorIntegration(
                    self.config['job_sources']['glassdoor']
                )
                logger.info("Glassdoor integration initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Glassdoor integration: {str(e)}")

    async def search_jobs(self,
                       keywords: List[str],
                       location: Optional[str] = None,
                       job_type: Optional[str] = None,
                       experience_level: Optional[str] = None,
                       remote: Optional[bool] = None,
                       posted_within_days: Optional[int] = None,
                       salary_min: Optional[int] = None,
                       sources: Optional[List[str]] = None,
                       page: int = 1,
                       results_per_page: int = 25) -> List[JobListing]:
        """Search for jobs across all enabled sources.
        
        Args:
            keywords: List of keywords to search for
            location: Location to search in
            job_type: Type of job (full-time, part-time, contract)
            experience_level: Required experience level
            remote: Whether to search for remote jobs
            posted_within_days: Only show jobs posted within this many days
            salary_min: Minimum salary requirement
            sources: Optional list of sources to search (e.g., ['linkedin', 'indeed'])
            page: Page number for pagination
            results_per_page: Number of results per page
            
        Returns:
            List[JobListing]: Combined list of job listings from all sources
        """
        if not sources:
            sources = list(self.job_sources.keys())
        else:
            sources = [s.lower() for s in sources]

        # Create tasks for each enabled source
        tasks = []
        for source in sources:
            if source in self.job_sources:
                tasks.append(
                    self.job_sources[source].search_jobs(
                        keywords=keywords,
                        location=location,
                        job_type=job_type,
                        experience_level=experience_level,
                        remote=remote,
                        posted_within_days=posted_within_days,
                        salary_min=salary_min,
                        page=page,
                        results_per_page=results_per_page
                    )
                )

        # Run all searches concurrently
        results = []
        if tasks:
            try:
                search_results = await asyncio.gather(*tasks, return_exceptions=True)
                for source_results in search_results:
                    if isinstance(source_results, list):
                        results.extend(source_results)
                    else:
                        logger.error(f"Search failed for a source: {str(source_results)}")
            except Exception as e:
                logger.error(f"Error during concurrent job search: {str(e)}")

        # Sort results by posting date (newest first)
        results.sort(
            key=lambda x: x.posted_date or datetime.min,
            reverse=True
        )

        return results

    async def get_job_details(self, job_id: str, source: str) -> Optional[JobListing]:
        """Get detailed information about a specific job.
        
        Args:
            job_id: ID of the job to get details for
            source: Source platform of the job (linkedin, indeed, glassdoor)
            
        Returns:
            Optional[JobListing]: Job listing with full details if found
        """
        source = source.lower()
        if source not in self.job_sources:
            logger.error(f"Unknown job source: {source}")
            return None

        try:
            return await self.job_sources[source].get_job_details(job_id)
        except Exception as e:
            logger.error(f"Error getting job details from {source}: {str(e)}")
            return None

    async def apply_to_job(self,
                        job_id: str,
                        source: str,
                        resume_path: str,
                        cover_letter_path: Optional[str] = None,
                        answers: Optional[Dict[str, str]] = None) -> bool:
        """Apply to a job using the appropriate source integration.
        
        Args:
            job_id: ID of the job to apply to
            source: Source platform of the job
            resume_path: Path to resume file
            cover_letter_path: Optional path to cover letter
            answers: Optional dictionary of answers to application questions
            
        Returns:
            bool: True if application was successful
        """
        source = source.lower()
        if source not in self.job_sources:
            logger.error(f"Unknown job source: {source}")
            return False

        try:
            return await self.job_sources[source].apply_to_job(
                job_id=job_id,
                resume_path=resume_path,
                cover_letter_path=cover_letter_path,
                answers=answers
            )
        except Exception as e:
            logger.error(f"Error applying to job from {source}: {str(e)}")
            return False

    async def check_application_status(self, job_id: str, source: str) -> Dict[str, Any]:
        """Check the status of an application.
        
        Args:
            job_id: ID of the job to check status for
            source: Source platform of the job
            
        Returns:
            Dict with application status information
        """
        source = source.lower()
        if source not in self.job_sources:
            logger.error(f"Unknown job source: {source}")
            return {'error': 'Unknown job source'}

        try:
            return await self.job_sources[source].check_application_status(job_id)
        except NotImplementedError:
            return {'error': f'Status checking not supported for {source}'}
        except Exception as e:
            logger.error(f"Error checking application status from {source}: {str(e)}")
            return {'error': str(e)}

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        # Close all job source sessions
        close_tasks = []
        for source in self.job_sources.values():
            if hasattr(source, '__aexit__'):
                close_tasks.append(source.__aexit__(exc_type, exc_val, exc_tb))
        
        if close_tasks:
            await asyncio.gather(*close_tasks) 