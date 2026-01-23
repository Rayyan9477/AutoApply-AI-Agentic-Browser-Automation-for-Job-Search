"""
LinkedIn integration module using LinkedIn MCP.
This module provides functionality to interact with LinkedIn for job searching
and application submission.
"""

import os
import time
import json
import logging
import asyncio
import requests
import random
from typing import List, Dict, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Import configuration
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config.linkedin_mcp_config import LinkedInMCPConfig
from config.config import LinkedInConfig

# Import the compatibility module for LinkedIn MCP
from src.job_sources.linkedin_mcp_compat import create_linkedin_mcp, is_linkedin_mcp_available

# Set up logging with absolute path for the log file
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
log_file_path = os.path.join(project_root, "data", "linkedin_integration.log")

# Ensure log directory exists
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Custom exceptions for better error handling
class LinkedInAuthError(Exception):
    """Exception raised for LinkedIn authentication errors."""
    pass

class LinkedInRateLimitError(Exception):
    """Exception raised for LinkedIn rate limiting."""
    pass

class LinkedInNetworkError(Exception):
    """Exception raised for LinkedIn network errors."""
    pass

def linkedin_error_handler(func: Callable) -> Callable:
    """
    Decorator to handle common LinkedIn API errors with appropriate logging and exception handling.
    
    Args:
        func: The function to wrap
        
    Returns:
        Wrapped function with error handling
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            logger.error(f"LinkedIn network connection error: {e}")
            raise LinkedInNetworkError(f"Network connection error: {e}") from e
        except requests.exceptions.Timeout as e:
            logger.error(f"LinkedIn request timeout: {e}")
            raise LinkedInNetworkError(f"Request timeout: {e}") from e
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error(f"LinkedIn rate limit exceeded: {e}")
                raise LinkedInRateLimitError(f"Rate limit exceeded: {e}") from e
            elif e.response.status_code in (401, 403):
                logger.error(f"LinkedIn authentication error: {e}")
                raise LinkedInAuthError(f"Authentication error: {e}") from e
            else:
                logger.error(f"LinkedIn HTTP error: {e}")
                raise
        except Exception as e:
            logger.error(f"Unexpected LinkedIn error: {e}")
            raise
    return wrapper

class LinkedInIntegration:
    """
    Class for LinkedIn integration using LinkedIn MCP.
    This class provides methods to interact with LinkedIn for job searching
    and application submission.
    """

    def __init__(self, config: Optional[Union[LinkedInMCPConfig, LinkedInConfig]] = None):
        """
        Initialize the LinkedInIntegration with configuration settings.
        
        Args:
            config: Configuration settings for LinkedIn integration.
                   If None, default settings will be used.
        """
        # Handle different config types - either LinkedInMCPConfig or LinkedInConfig
        if isinstance(config, LinkedInConfig):
            # Convert from general config to MCP config
            self.config = LinkedInMCPConfig(
                client_id=config.client_id.get_secret_value() if hasattr(config.client_id, 'get_secret_value') else config.client_id,
                client_secret=config.client_secret.get_secret_value() if hasattr(config.client_secret, 'get_secret_value') else config.client_secret,
                redirect_uri=config.redirect_uri
            )
            # Use session_path or session_storage_path from LinkedInConfig
            if hasattr(config, 'session_storage_path'):
                self.config.session_storage_path = config.session_storage_path
            elif hasattr(config, 'session_path'):
                self.config.session_storage_path = config.session_path
        else:
            # Use the provided MCP config or create a default one
            self.config = config or LinkedInMCPConfig()

        # Create necessary directories
        self.config.session_storage_path = os.path.join(project_root, "data", "sessions")
        os.makedirs(self.config.session_storage_path, exist_ok=True)
        
        self._setup_mcp_server()
        self.access_token = None
        self.token_expiry = None
        
    def _setup_mcp_server(self) -> None:
        """Set up the LinkedIn MCP server connection."""
        try:
            os.makedirs(self.config.session_storage_path, exist_ok=True)
            
            # Check if API credentials are configured
            if not self.config.client_id or not self.config.client_secret:
                logger.info("LinkedIn MCP API credentials not configured - using cookie-based authentication instead")
                self.mcp_server = None
                return
                
            # Use our compatibility module to check for MCP availability
            mcp_available = is_linkedin_mcp_available()
            if (mcp_available):
                # Create MCP server using compatibility layer
                config_dict = {
                    "client_id": self.config.client_id,
                    "client_secret": self.config.client_secret,
                    "redirect_uri": self.config.redirect_uri,
                    "session_storage_path": self.config.session_storage_path
                }
                
                # Get MCP instance through our compatibility layer
                self.mcp_server = create_linkedin_mcp(config_dict)
                logger.info("LinkedIn MCP server initialized successfully")
            else:
                logger.warning("LinkedIn MCP package not available - cannot use API features")
                self.mcp_server = None
                
        except Exception as e:
            logger.error(f"Error setting up LinkedIn MCP server: {e}")
            self.mcp_server = None
            
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((LinkedInNetworkError, LinkedInRateLimitError))
    )
    @linkedin_error_handler
    async def authenticate(self) -> bool:
        """
        Authenticate with LinkedIn using OAuth 2.0 or saved cookies.
        Uses retry mechanism for handling transient failures.
        
        Returns:
            True if authentication was successful, False otherwise.
        """
        # First check if we have a valid token
        if self._is_token_valid():
            logger.info("Using existing valid LinkedIn token")
            return True
            
        # Then check if we have saved cookies
        cookies_file = os.path.join(self.config.session_storage_path, "linkedin_cookies.json")
        if os.path.exists(cookies_file):
            logger.info("Found saved LinkedIn cookies, attempting to use them")
            try:
                # Import required modules
                from src.utils.browser_automation import JobSearchBrowser
                from config.browser_config import BrowserConfig
                
                # Create custom browser config with headless mode initially disabled
                browser_config = BrowserConfig()
                browser_config.headless = False  # Use headful mode for initial login
                
                # Initialize browser
                browser = JobSearchBrowser(browser_config)
                
                # Use the browser to test if cookies are valid by visiting LinkedIn
                authenticated = await browser.test_linkedin_cookies(cookies_file)
                
                if authenticated:
                    logger.info("Successfully authenticated with LinkedIn using saved cookies")
                    return True
                else:
                    logger.warning("Saved cookies are invalid or expired")
            except Exception as e:
                logger.error(f"Error authenticating with saved cookies: {e}")
        
        # If no cookies or they're invalid, try manual login
        try:
            logger.info("No valid authentication found, attempting manual login")
            
            # Import required modules for browser automation
            from src.utils.browser_automation import JobSearchBrowser
            from config.browser_config import BrowserConfig
            
            # Create custom browser config with headless mode disabled for manual login
            browser_config = BrowserConfig()
            browser_config.headless = False  # Must use headful mode for manual login
            
            # Initialize browser
            browser = JobSearchBrowser(browser_config)
            
            # Launch browser for manual login
            authenticated = await browser.login_to_linkedin_manual()
            
            if authenticated:
                logger.info("Successfully authenticated with LinkedIn via manual login")
                return True
            else:
                logger.warning("Manual LinkedIn authentication failed")
                return False
                
        except Exception as e:
            logger.error(f"Error during LinkedIn authentication: {e}")
            return False
            
    def _is_token_valid(self) -> bool:
        """
        Check if the current access token is valid.
        
        Returns:
            True if the token is valid, False otherwise.
        """
        if not self.access_token or not self.token_expiry:
            # Try to load from session
            token_info = self._load_token()
            if (token_info):
                self.access_token = token_info.get("access_token")
                expires_at = token_info.get("expires_at")
                if expires_at:
                    self.token_expiry = datetime.fromisoformat(expires_at)
            else:
                return False
                
        # Check if token is still valid
        if self.token_expiry and datetime.now() < self.token_expiry - timedelta(minutes=5):  # 5-minute buffer
            return True
            
        return False
        
    def _save_token(self, token_info: Dict[str, Any]) -> None:
        """
        Save the token information to a file.
        
        Args:
            token_info: Token information to save.
        """
        try:
            # Add expiry timestamp
            if "expires_in" in token_info:
                expires_at = datetime.now() + timedelta(seconds=token_info["expires_in"])
                token_info["expires_at"] = expires_at.isoformat()
                
            session_file = os.path.join(self.config.session_storage_path, "linkedin_session.json")
            with open(session_file, "w") as f:
                json.dump(token_info, f, indent=2)
                
            logger.info(f"LinkedIn session saved to {session_file}")
            
        except Exception as e:
            logger.error(f"Error saving LinkedIn session: {e}")
            
    def _load_token(self) -> Dict[str, Any]:
        """
        Load token information from a file.
        
        Returns:
            Token information if available, empty dictionary otherwise.
        """
        try:
            session_file = os.path.join(self.config.session_storage_path, "linkedin_session.json")
            if not os.path.exists(session_file):
                return {}
                
            with open(session_file, "r") as f:
                token_info = json.load(f)
                
            logger.info(f"LinkedIn session loaded from {session_file}")
            return token_info
            
        except Exception as e:
            logger.error(f"Error loading LinkedIn session: {e}")
            return {}
            
    async def search_jobs(self, 
                   keywords: Optional[List[str]] = None,
                   location: Optional[str] = None,
                   count: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for jobs on LinkedIn using web scraping since direct API is limited.
        
        Args:
            keywords: List of job keywords to search for.
            location: Location to search for jobs.
            count: Maximum number of jobs to return.
            
        Returns:
            A list of job listings.
        """
        try:
            # Import the web scraper dynamically to avoid circular imports
            from src.utils.browser_automation import JobSearchBrowser
            from config.browser_config import BrowserConfig
            
            # Initialize the browser
            browser = JobSearchBrowser(BrowserConfig())
            
            # Convert keywords list to string
            keywords_str = " ".join(keywords) if keywords else ""
            
            # Use browser automation to search for jobs with retry logic
            max_retries = 3
            retry_count = 0
            job_listings = []
            
            while retry_count < max_retries:
                try:
                    logger.info(f"Searching LinkedIn for jobs: {keywords_str} in {location} (attempt {retry_count + 1})")
                    job_listings = await browser.search_for_jobs(
                        keywords=[keywords_str] if keywords_str else None,
                        location=location,
                        job_site="linkedin"
                    )
                    
                    # If we got results, break out of retry loop
                    if job_listings:
                        break
                        
                    # If no results, wait and retry with slightly modified query
                    logger.warning(f"No results found on attempt {retry_count + 1}. Retrying...")
                    retry_count += 1
                    
                    # Add small variations to search on retry
                    if retry_count == 1 and keywords:
                        # On first retry, try without location constraint
                        location = None
                    elif retry_count == 2 and len(keywords) > 1:
                        # On second retry, try with just the first keyword
                        keywords_str = keywords[0] if keywords else ""
                    
                    # Wait between retries with exponential backoff
                    backoff_time = 2 ** retry_count
                    await asyncio.sleep(backoff_time)
                    
                except Exception as e:
                    logger.error(f"Error during job search attempt {retry_count + 1}: {e}")
                    retry_count += 1
                    await asyncio.sleep(5)
            
            # Limit results if count is specified
            if count and len(job_listings) > count:
                job_listings = job_listings[:count]
            
            # Save job listings
            self._save_job_listings(job_listings)
            
            logger.info(f"Found {len(job_listings)} jobs on LinkedIn")
            return job_listings
            
        except Exception as e:
            logger.error(f"Error searching LinkedIn jobs: {e}")
            return []
            
    def _parse_linkedin_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse LinkedIn job data into a standardized format.
        
        Args:
            job_data: Job data from LinkedIn API.
            
        Returns:
            A standardized job listing dictionary.
        """
        try:
            job_listing = {}
            
            # Extract basic job information
            if "title" in job_data:
                job_listing["job_title"] = job_data["title"]
                
            if "company" in job_data and "name" in job_data["company"]:
                job_listing["company"] = job_data["company"]["name"]
                
            if "location" in job_data:
                job_listing["location"] = job_data["location"]
                
            # Extract job URL
            if "job_id" in job_data:
                job_listing["url"] = f"https://www.linkedin.com/jobs/view/{job_data['job_id']}/"
                job_listing["job_id"] = job_data["job_id"]
                
            # Extract posting date
            if "posted_at" in job_data:
                job_listing["posted_date"] = job_data["posted_at"]
                
            # Extract application URL if available
            if "application_url" in job_data:
                job_listing["application_url"] = job_data["application_url"]
                
            return job_listing
            
        except Exception as e:
            logger.error(f"Error parsing LinkedIn job: {e}")
            return {}
            
    def _save_job_listings(self, job_listings: List[Dict[str, Any]]) -> None:
        """
        Save LinkedIn job listings to a JSON file.
        
        Args:
            job_listings: List of job listings to save.
        """
        try:
            output_file = "../data/linkedin_job_listings.json"
            with open(output_file, "w") as f:
                json.dump(job_listings, f, indent=2)
                
            logger.info(f"Saved {len(job_listings)} LinkedIn job listings to {output_file}")
            
        except Exception as e:
            logger.error(f"Error saving LinkedIn job listings: {e}")
            
    async def get_job_description(self, job_id: str) -> Dict[str, Any]:
        """
        Get job description for a specific job ID using web scraping.
        
        Args:
            job_id: LinkedIn job ID.
            
        Returns:
            Dictionary containing job details including description.
        """
        try:
            # Import web scraping module dynamically
            from src.utils.web_scraping import JobDetailsScraper
            
            # Create URL for the job
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            
            # Initialize scraper
            scraper = JobDetailsScraper()
            
            # Scrape job details
            logger.info(f"Scraping job details for job ID: {job_id}")
            job_details = await scraper.scrape_job_details(job_url)
            
            if not job_details:
                logger.error(f"Failed to scrape job details for job ID: {job_id}")
                return {}
                
            # Format return value to match expected structure
            result = {
                "job_id": job_id,
                "title": job_details.get("job_title", "Unknown Position"),
                "description": job_details.get("description", ""),
                "company": {
                    "name": job_details.get("company", "Unknown Company"),
                    "description": job_details.get("company_description", "")
                },
                "location": job_details.get("location", "Unknown Location"),
                "url": job_url
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting job description for job ID {job_id}: {e}")
            return {}
            
    async def get_user_profile(self) -> Dict[str, Any]:
        """
        Get user profile by loading candidate profile from JSON file.
        
        Returns:
            Dictionary containing user profile data.
        """
        try:
            # Define path to candidate profile JSON
            profile_path = os.path.join(project_root, "data", "candidate_profile.json")
            
            # Check if file exists
            if not os.path.exists(profile_path):
                logger.error(f"Candidate profile not found at {profile_path}")
                return {}
                
            # Load profile from file
            with open(profile_path, "r") as f:
                profile = json.load(f)
                
            logger.info("Successfully loaded candidate profile")
            
            # Transform to match expected LinkedIn API format
            transformed_profile = {
                "first_name": profile.get("name", "").split()[0] if profile.get("name") else "",
                "last_name": " ".join(profile.get("name", "").split()[1:]) if profile.get("name") else "",
                "email": profile.get("email", ""),
                "headline": profile.get("summary", ""),
                "phone_numbers": [profile.get("phone", "")] if profile.get("phone") else [],
                "location": {
                    "city": profile.get("location", "").split(",")[0].strip() if profile.get("location") else "",
                    "state": profile.get("location", "").split(",")[1].strip() if profile.get("location") and len(profile.get("location", "").split(",")) > 1 else "",
                    "country": profile.get("location", "").split(",")[-1].strip() if profile.get("location") else ""
                },
                "skills": profile.get("skills", []),
                "experience": [
                    {
                        "title": exp.get("title", ""),
                        "company": exp.get("company", ""),
                        "start_date": {"year": exp.get("dates", "").split("-")[0].strip() if exp.get("dates") else ""},
                        "end_date": {"year": exp.get("dates", "").split("-")[1].strip() if exp.get("dates") and "-" in exp.get("dates", "") else "Present"},
                        "description": exp.get("description", "")
                    }
                    for exp in profile.get("experience", [])
                ],
                "education": [
                    {
                        "school": edu.get("institution", ""),
                        "degree": edu.get("degree", ""),
                        "field_of_study": edu.get("field", ""),
                        "end_date": {"year": edu.get("year", "")}
                    }
                    for edu in profile.get("education", [])
                ]
            }
            
            return transformed_profile
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {}
            
    async def apply_to_job(self, 
                     job_id: str,
                     resume_path: Optional[str] = None,
                     cover_letter_path: Optional[str] = None) -> bool:
        """
        Apply to LinkedIn job using browser automation.
        
        Args:
            job_id: LinkedIn job ID.
            resume_path: Path to resume file.
            cover_letter_path: Optional path to cover letter file.
            
        Returns:
            True if application was successful, False otherwise.
        """
        try:
            # Check if we can proceed with application (rate limiting)
            if not self._check_rate_limit_applications():
                logger.warning("Application rate limit exceeded. Skipping application.")
                return False
                
            # Import the browser automation module dynamically
            from src.utils.browser_automation import JobSearchBrowser
            from config.browser_config import BrowserConfig
            
            # Create the job URL
            job_url = f"https://www.linkedin.com/jobs/view/{job_id}/"
            
            # Initialize browser
            browser = JobSearchBrowser(BrowserConfig())
            
            # Extract phone number from config
            phone = self.config.default_phone_number
            
            # Log the attempt
            logger.info(f"Attempting to apply to job: {job_id} with resume: {resume_path}")
            
            # Apply to the job
            success = await browser.apply_to_linkedin_job(
                job_url=job_url,
                resume_path=resume_path,
                cover_letter_path=cover_letter_path,
                phone=phone
            )
            
            if success:
                # Update application history
                self._update_application_history(job_id)
                logger.info(f"Successfully applied to job: {job_id}")
            else:
                logger.warning(f"Failed to apply to job: {job_id}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error applying to job {job_id}: {e}")
            return False
            
    def _check_rate_limit_applications(self) -> bool:
        """
        Check if we've exceeded the application rate limit.
        
        Returns:
            True if we can proceed with the application, False otherwise.
        """
        try:
            # Load application history
            history_file = os.path.join(self.config.session_storage_path, "application_history.json")
            history = []
            
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    history = json.load(f)
                    
            # Count applications in the last hour
            one_hour_ago = datetime.now() - timedelta(hours=1)
            recent_applications = [
                app for app in history 
                if datetime.fromisoformat(app["timestamp"]) > one_hour_ago
            ]
            
            # Count applications today
            today = datetime.now().date()
            today_applications = [
                app for app in history 
                if datetime.fromisoformat(app["timestamp"]).date() == today
            ]
            
            # Check rate limits
            if len(recent_applications) >= self.config.rate_limit_applications:
                logger.warning(f"Application rate limit exceeded: {len(recent_applications)} applications in the last hour")
                return False
                
            if len(today_applications) >= self.config.max_applications_per_day:
                logger.warning(f"Daily application limit exceeded: {len(today_applications)} applications today")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error checking application rate limit: {e}")
            # Default to allowing the application if we can't check the rate limit
            return True
            
    def _update_application_history(self, job_id: str) -> None:
        """
        Update the application history after applying to a job.
        
        Args:
            job_id: LinkedIn job ID that was applied to.
        """
        try:
            # Load application history
            history_file = os.path.join(self.config.session_storage_path, "application_history.json")
            history = []
            
            if os.path.exists(history_file):
                with open(history_file, "r") as f:
                    history = json.load(f)
                    
            # Add new application to history
            history.append({
                "job_id": job_id,
                "timestamp": datetime.now().isoformat()
            })
            
            # Save updated history
            with open(history_file, "w") as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error updating application history: {e}")

    async def generate_application_materials(self, 
                              job_id: str,
                              cover_letter_type: Optional[str] = None) -> Dict[str, str]:
        """
        Generate resume and cover letter for a specific job.
        
        Args:
            job_id: LinkedIn job ID.
            cover_letter_type: Type of cover letter to generate (standard, creative, technical, 
                               executive, career_change, referral). If None, will auto-select.
            
        Returns:
            Dictionary with paths to generated resume and cover letter.
        """
        result = {
            "resume_path": "",
            "cover_letter_path": "",
            "job_title": "",
            "company": ""
        }
        
        try:
            # Get job description
            job_details = await self.get_job_description(job_id)
            
            if not job_details:
                logger.error(f"Failed to get job description for job ID: {job_id}")
                return result
                
            job_title = job_details.get("title", "Unknown Position")
            company_name = job_details.get("company", {}).get("name", "Unknown Company")
            
            # Get full job description text
            job_description_text = job_details.get("description", "")
            if not job_description_text:
                logger.error(f"Job description text not found for job ID: {job_id}")
                return result
                
            # Get user profile to use as candidate profile
            user_profile = await self.get_user_profile()
            if not user_profile:
                logger.error("Failed to get user profile")
                return result
                
            # Transform LinkedIn profile into candidate profile
            candidate_profile = self._transform_profile_to_candidate(user_profile)
            
            # Get company information
            company_info = job_details.get("company", {}).get("description", "")
            if not company_info:
                company_info = f"{company_name} is a company hiring for a {job_title} position."
            
            # Import the resume generator dynamically to avoid circular imports
            from src.resume_cover_letter_generator import ResumeGenerator, CoverLetterTemplate
            
            # Create resume generator
            resume_generator = ResumeGenerator()
            
            # Generate resume
            resume_path, resume_content = resume_generator.generate_resume(
                job_description=job_description_text,
                candidate_profile=candidate_profile
            )
            
            # Determine cover letter type
            template_type = None
            if cover_letter_type:
                try:
                    template_type = CoverLetterTemplate[cover_letter_type.upper()]
                except (KeyError, AttributeError):
                    logger.warning(f"Invalid cover letter type: {cover_letter_type}. Auto-selecting type.")
            
            # Generate cover letter
            cover_letter_path, _ = resume_generator.generate_cover_letter(
                job_description=job_description_text,
                candidate_resume=resume_content,
                company_info=company_info,
                template_type=template_type
            )
            
            result["resume_path"] = resume_path
            result["cover_letter_path"] = cover_letter_path
            result["job_title"] = job_title
            result["company"] = company_name
            
            logger.info(f"Generated application materials for {job_title} at {company_name}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error generating application materials: {e}")
            return result
            
    def _transform_profile_to_candidate(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform LinkedIn profile into candidate profile format for resume generation.
        
        Args:
            profile: LinkedIn profile data.
            
        Returns:
            Candidate profile dictionary.
        """
        candidate = {}
        
        try:
            # Basic information
            candidate["name"] = f"{profile.get('first_name', '')} {profile.get('last_name', '')}".strip()
            
            if "email" in profile:
                candidate["email"] = profile["email"]
                
            if "phone_numbers" in profile and profile["phone_numbers"]:
                candidate["phone"] = profile["phone_numbers"][0]
                
            # Location
            if "location" in profile:
                location_parts = []
                if "city" in profile["location"]:
                    location_parts.append(profile["location"]["city"])
                if "state" in profile["location"]:
                    location_parts.append(profile["location"]["state"])
                if "country" in profile["location"]:
                    location_parts.append(profile["location"]["country"])
                    
                candidate["location"] = ", ".join(location_parts)
                
            # Summary/Headline
            if "headline" in profile:
                candidate["summary"] = profile["headline"]
                
            # Experience
            if "experience" in profile and profile["experience"]:
                experiences = []
                for exp in profile["experience"]:
                    experience = {}
                    
                    if "title" in exp:
                        experience["title"] = exp["title"]
                        
                    if "company" in exp:
                        experience["company"] = exp["company"]["name"] if isinstance(exp["company"], dict) else exp["company"]
                        
                    # Format dates
                    if "start_date" in exp:
                        start_year = exp["start_date"].get("year", "")
                        experience["start"] = str(start_year)
                        
                    if "end_date" in exp:
                        end_year = exp["end_date"].get("year", "Present")
                        experience["end"] = str(end_year)
                        
                    experience["duration"] = f"{experience.get('start', '')} - {experience.get('end', 'Present')}"
                    
                    if "description" in exp:
                        experience["description"] = exp["description"]
                        
                    experiences.append(experience)
                    
                candidate["experience"] = experiences
                
            # Education
            if "education" in profile and profile["education"]:
                education = []
                for edu in profile["education"]:
                    edu_item = {}
                    
                    if "school" in edu:
                        edu_item["institution"] = edu["school"]["name"] if isinstance(edu["school"], dict) else edu["school"]
                        
                    if "degree" in edu:
                        edu_item["degree"] = edu["degree"]["name"] if isinstance(edu["degree"], dict) else edu["degree"]
                        
                    if "field_of_study" in edu:
                        edu_item["field"] = edu["field_of_study"]
                        
                    if "end_date" in edu and "year" in edu["end_date"]:
                        edu_item["year"] = str(edu["end_date"]["year"])
                        
                    education.append(edu_item)
                    
                candidate["education"] = education
                
            # Skills
            if "skills" in profile and profile["skills"]:
                skills = []
                for skill in profile["skills"]:
                    if isinstance(skill, dict):
                        skills.append(skill.get("name", ""))
                    else:
                        skills.append(skill)
                        
                candidate["skills"] = skills
                
        except Exception as e:
            logger.error(f"Error transforming profile to candidate: {e}")
            
        return candidate
    
    async def full_application_workflow(self, 
                                 keywords: List[str], 
                                 location: str,
                                 count: int = 5,
                                 auto_apply: bool = False) -> List[Dict[str, Any]]:
        """
        Execute full job application workflow: search, generate materials, and optionally apply.
        
        Args:
            keywords: List of job keywords to search for.
            location: Location to search for jobs.
            count: Number of job results to process.
            auto_apply: Whether to automatically apply to jobs.
            
        Returns:
            List of dictionaries with job and application information.
        """
        results = []
        
        try:
            # 1. Search for jobs
            jobs = await self.search_jobs(keywords=keywords, location=location, count=count)
            
            if not jobs:
                logger.info("No jobs found")
                return results
                
            logger.info(f"Processing {len(jobs)} jobs for application workflow")
            
            # 2. For each job, generate application materials
            for job in jobs:
                job_id = job.get("job_id")
                if not job_id:
                    logger.warning(f"Job ID not found: {job}")
                    continue
                    
                logger.info(f"Processing job: {job.get('job_title')} at {job.get('company')}")
                
                # Generate application materials
                materials = await self.generate_application_materials(job_id)
                
                result = {
                    "job": job,
                    "materials": materials
                }
                
                # 3. Apply to job if auto-apply is enabled
                if auto_apply and self.config.auto_apply_enabled:
                    if materials["resume_path"] and materials["cover_letter_path"]:
                        # Wait a random time to appear more human-like
                        wait_time = self.config.min_application_delay + (
                            self.config.max_application_delay - self.config.min_application_delay
                        ) * random.random()
                        
                        logger.info(f"Waiting {wait_time:.1f} seconds before applying...")
                        await asyncio.sleep(wait_time)
                        
                        # Apply to job
                        success = await self.apply_to_job(
                            job_id=job_id,
                            resume_path=materials["resume_path"],
                            cover_letter_path=materials["cover_letter_path"]
                        )
                        
                        result["applied"] = success
                        
                results.append(result)
                
            return results
            
        except Exception as e:
            logger.error(f"Error in full application workflow: {e}")
            return results


# Example usage
async def main():
    linkedin = LinkedInIntegration()
    authenticated = await linkedin.authenticate()
    
    if authenticated:
        jobs = await linkedin.search_jobs(
            keywords=["software engineer", "python"],
            location="New York"
        )
        
        print(f"Found {len(jobs)} jobs on LinkedIn")
        
        # Get the user's profile
        profile = await linkedin.get_user_profile()
        print(f"User profile: {profile.get('first_name', '')} {profile.get('last_name', '')}")
        
        # Get job details for the first job
        if jobs:
            job_id = jobs[0].get("job_id")
            if job_id:
                job_details = await linkedin.get_job_description(job_id)
                print(f"Job details: {job_details}")


if __name__ == "__main__":
    asyncio.run(main())