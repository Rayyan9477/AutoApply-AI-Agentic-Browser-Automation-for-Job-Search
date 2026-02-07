"""
Unit tests for the LinkedIn integration module.
"""
import os
import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from job_application_automation.src.job_sources.linkedin_integration import (
    LinkedInIntegration,
    LinkedInAuthError,
    LinkedInRateLimitError,
    LinkedInNetworkError
)
from job_application_automation.src.job_sources.linkedin_mcp_compat import MockLinkedInMCP, MockMCPConfig


class TestLinkedInIntegration:
    """Tests for LinkedIn integration."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock LinkedIn config."""
        config = MagicMock()
        config.client_id = "test_client_id"
        config.client_secret = "test_client_secret"
        config.redirect_uri = "http://localhost:8000/callback"
        config.session_storage_path = "/tmp/test_sessions"
        config.rate_limit_applications = 5
        config.max_applications_per_day = 10
        config.min_application_delay = 5
        config.max_application_delay = 15
        config.auto_apply_enabled = False
        config.default_phone_number = "555-1234"
        return config

    @pytest.fixture
    def mock_job(self):
        """Create a mock job listing."""
        return {
            "job_id": "test_job_123",
            "job_title": "Senior Software Engineer",
            "company": "Test Tech Corp",
            "location": "New York, NY",
            "url": "https://www.linkedin.com/jobs/view/test_job_123/",
            "posted_date": "2025-04-25"
        }

    @pytest.fixture
    def mock_job_description(self):
        """Create a mock job description."""
        return {
            "job_id": "test_job_123",
            "title": "Senior Software Engineer",
            "description": "We are looking for a senior software engineer with Python experience.",
            "company": {
                "name": "Test Tech Corp",
                "description": "Test Tech Corp is a leading technology company."
            },
            "location": "New York, NY",
            "url": "https://www.linkedin.com/jobs/view/test_job_123/"
        }

    @pytest.fixture
    def mock_user_profile(self):
        """Create a mock user profile."""
        return {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "headline": "Senior Software Engineer with 8+ years of experience",
            "phone_numbers": ["555-5678"],
            "location": {
                "city": "New York",
                "state": "NY",
                "country": "United States"
            },
            "skills": ["Python", "JavaScript", "AWS"],
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Previous Company",
                    "start_date": {"year": "2020"},
                    "end_date": {"year": "Present"},
                    "description": "Lead developer on multiple projects."
                }
            ],
            "education": [
                {
                    "school": "Test University",
                    "degree": "Bachelor's",
                    "field_of_study": "Computer Science",
                    "end_date": {"year": "2015"}
                }
            ]
        }

    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    def test_init(self, mock_create_mcp, mock_is_available, mock_config):
        """Test initialization of LinkedIn integration."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())

        linkedin = LinkedInIntegration(mock_config)
        
        assert linkedin.config == mock_config
        assert isinstance(linkedin.mcp_server, MockLinkedInMCP)
        assert linkedin.access_token is None
        assert linkedin.token_expiry is None

    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    def test_init_no_api_credentials(self, mock_create_mcp, mock_is_available, mock_config):
        """Test initialization without API credentials."""
        mock_config.client_id = ""
        mock_config.client_secret = ""
        mock_is_available.return_value = True

        linkedin = LinkedInIntegration(mock_config)
        
        assert linkedin.mcp_server is None
        mock_create_mcp.assert_not_called()

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    async def test_is_token_valid(self, mock_open, mock_path_exists, mock_create_mcp, mock_is_available, mock_config):
        """Test token validation."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        mock_path_exists.return_value = True
        
        # Mock file read with valid token
        mock_open().__enter__().read.return_value = json.dumps({
            "access_token": "test_token",
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat()
        })
        
        linkedin = LinkedInIntegration(mock_config)
        is_valid = linkedin._is_token_valid()
        
        assert is_valid is True
        assert linkedin.access_token == "test_token"

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    @patch("os.path.exists")
    async def test_is_token_valid_expired(self, mock_path_exists, mock_create_mcp, mock_is_available, mock_config):
        """Test expired token validation."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        mock_path_exists.return_value = False
        
        linkedin = LinkedInIntegration(mock_config)
        linkedin.access_token = "test_token"
        linkedin.token_expiry = datetime.now() - timedelta(hours=1)
        
        is_valid = linkedin._is_token_valid()
        
        assert is_valid is False

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    @patch("job_application_automation.src.job_sources.linkedin_integration.JobSearchBrowser")
    async def test_search_jobs(self, mock_browser_class, mock_create_mcp, mock_is_available, mock_config, mock_job):
        """Test job search functionality."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        
        # Setup mock browser
        mock_browser = MagicMock()
        mock_browser.search_for_jobs = AsyncMock(return_value=[mock_job])
        mock_browser_class.return_value = mock_browser
        
        linkedin = LinkedInIntegration(mock_config)
        
        # Mock the _save_job_listings method
        linkedin._save_job_listings = MagicMock()
        
        # Call search_jobs
        results = await linkedin.search_jobs(
            keywords=["software engineer", "python"],
            location="New York",
            count=5
        )
        
        assert len(results) == 1
        assert results[0] == mock_job
        mock_browser.search_for_jobs.assert_called_once()
        linkedin._save_job_listings.assert_called_once_with([mock_job])

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    @patch("job_application_automation.src.job_sources.linkedin_integration.JobDetailsScraper")
    async def test_get_job_description(self, mock_scraper_class, mock_create_mcp, mock_is_available, mock_config, mock_job):
        """Test getting job description."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        
        # Setup mock scraper
        mock_scraper = MagicMock()
        mock_scraper.scrape_job_details = AsyncMock(return_value={
            "job_title": "Senior Software Engineer",
            "company": "Test Tech Corp",
            "description": "Job description text",
            "location": "New York, NY",
            "company_description": "Company description"
        })
        mock_scraper_class.return_value = mock_scraper
        
        linkedin = LinkedInIntegration(mock_config)
        
        # Call get_job_description
        job_details = await linkedin.get_job_description("test_job_123")
        
        assert job_details["job_id"] == "test_job_123"
        assert job_details["title"] == "Senior Software Engineer"
        assert job_details["company"]["name"] == "Test Tech Corp"
        assert "description" in job_details
        mock_scraper.scrape_job_details.assert_called_once()

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("json.load")
    async def test_get_user_profile(self, mock_json_load, mock_open, mock_path_exists, mock_create_mcp, 
                              mock_is_available, mock_config, mock_user_profile):
        """Test getting user profile."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        mock_path_exists.return_value = True
        
        # Mock JSON load with profile data
        profile_data = {
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone": "555-5678",
            "summary": "Senior Software Engineer with 8+ years of experience",
            "location": "New York, NY, United States",
            "skills": ["Python", "JavaScript", "AWS"],
            "experience": [
                {
                    "title": "Senior Software Engineer",
                    "company": "Previous Company",
                    "dates": "2020 - Present",
                    "description": "Lead developer on multiple projects."
                }
            ],
            "education": [
                {
                    "institution": "Test University",
                    "degree": "Bachelor's",
                    "field": "Computer Science",
                    "year": "2015"
                }
            ]
        }
        mock_json_load.return_value = profile_data
        
        linkedin = LinkedInIntegration(mock_config)
        
        # Call get_user_profile
        profile = await linkedin.get_user_profile()
        
        assert profile["first_name"] == "John"
        assert profile["last_name"] == "Doe"
        assert profile["email"] == "john.doe@example.com"
        assert profile["headline"] == "Senior Software Engineer with 8+ years of experience"
        assert len(profile["skills"]) == 3
        assert len(profile["experience"]) == 1
        assert len(profile["education"]) == 1
        mock_path_exists.assert_called_once()
        mock_open.assert_called_once()

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    @patch("job_application_automation.src.job_sources.linkedin_integration.JobSearchBrowser")
    async def test_apply_to_job(self, mock_browser_class, mock_create_mcp, mock_is_available, mock_config):
        """Test applying to a job."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        
        # Setup mock browser
        mock_browser = MagicMock()
        mock_browser.apply_to_linkedin_job = AsyncMock(return_value=True)
        mock_browser_class.return_value = mock_browser
        
        linkedin = LinkedInIntegration(mock_config)
        
        # Mock methods
        linkedin._check_rate_limit_applications = MagicMock(return_value=True)
        linkedin._update_application_history = MagicMock()
        
        # Call apply_to_job
        result = await linkedin.apply_to_job(
            job_id="test_job_123",
            resume_path="/path/to/resume.pdf",
            cover_letter_path="/path/to/cover_letter.pdf"
        )
        
        assert result is True
        mock_browser.apply_to_linkedin_job.assert_called_once()
        linkedin._check_rate_limit_applications.assert_called_once()
        linkedin._update_application_history.assert_called_once_with("test_job_123")

    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    @patch("os.path.exists")
    @patch("builtins.open", new_callable=MagicMock)
    @patch("json.load")
    def test_check_rate_limit_applications(self, mock_json_load, mock_open, mock_path_exists, 
                                     mock_create_mcp, mock_is_available, mock_config):
        """Test checking application rate limits."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        mock_path_exists.return_value = True
        
        # Setup history with applications within rate limit
        history = [
            {"job_id": "job1", "timestamp": (datetime.now() - timedelta(hours=2)).isoformat()},
            {"job_id": "job2", "timestamp": (datetime.now() - timedelta(hours=3)).isoformat()}
        ]
        mock_json_load.return_value = history
        
        linkedin = LinkedInIntegration(mock_config)
        
        # Test within limits
        result = linkedin._check_rate_limit_applications()
        assert result is True
        
        # Test exceeding hourly limit
        history = [
            {"job_id": "job1", "timestamp": datetime.now().isoformat()},
            {"job_id": "job2", "timestamp": datetime.now().isoformat()},
            {"job_id": "job3", "timestamp": datetime.now().isoformat()},
            {"job_id": "job4", "timestamp": datetime.now().isoformat()},
            {"job_id": "job5", "timestamp": datetime.now().isoformat()},
            {"job_id": "job6", "timestamp": datetime.now().isoformat()}
        ]
        mock_json_load.return_value = history
        
        result = linkedin._check_rate_limit_applications()
        assert result is False

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    async def test_transform_profile_to_candidate(self, mock_create_mcp, mock_is_available, 
                                         mock_config, mock_user_profile):
        """Test transforming LinkedIn profile to candidate format."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        
        linkedin = LinkedInIntegration(mock_config)
        
        # Call transform method
        candidate = linkedin._transform_profile_to_candidate(mock_user_profile)
        
        # Verify transformed profile
        assert candidate["name"] == "John Doe"
        assert candidate["email"] == "john.doe@example.com"
        assert candidate["phone"] == "555-5678"
        assert candidate["location"] == "New York, NY, United States"
        assert candidate["summary"] == "Senior Software Engineer with 8+ years of experience"
        assert len(candidate["skills"]) == 3
        assert len(candidate["experience"]) == 1
        assert len(candidate["education"]) == 1

    @pytest.mark.asyncio
    @patch("job_application_automation.src.job_sources.linkedin_mcp_compat.is_linkedin_mcp_available")
    @patch("job_application_automation.src.job_sources.linkedin_integration.create_linkedin_mcp")
    async def test_full_application_workflow(self, mock_create_mcp, mock_is_available, mock_config, mock_job):
        """Test the full application workflow."""
        mock_is_available.return_value = True
        mock_create_mcp.return_value = MockLinkedInMCP(MockMCPConfig())
        
        linkedin = LinkedInIntegration(mock_config)
        
        # Mock methods
        linkedin.search_jobs = AsyncMock(return_value=[mock_job])
        linkedin.generate_application_materials = AsyncMock(return_value={
            "resume_path": "/path/to/resume.pdf",
            "cover_letter_path": "/path/to/cover_letter.pdf",
            "job_title": "Senior Software Engineer",
            "company": "Test Tech Corp"
        })
        linkedin.apply_to_job = AsyncMock(return_value=True)
        
        # Call full workflow with auto-apply disabled
        results = await linkedin.full_application_workflow(
            keywords=["software engineer", "python"],
            location="New York",
            count=5,
            auto_apply=False
        )
        
        assert len(results) == 1
        assert "job" in results[0]
        assert "materials" in results[0]
        assert "applied" not in results[0]
        
        # Verify method calls
        linkedin.search_jobs.assert_called_once()
        linkedin.generate_application_materials.assert_called_once()
        linkedin.apply_to_job.assert_not_called()