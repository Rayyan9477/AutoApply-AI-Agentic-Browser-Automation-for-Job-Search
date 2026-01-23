"""
LinkedIn MCP compatibility module.
This module provides a wrapper for LinkedIn MCP that gracefully handles missing imports.
"""

import os
import logging
from typing import Any, Dict, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Flag to indicate if linkedin_mcp module is available
LINKEDIN_MCP_AVAILABLE = False

# Mock classes for when linkedin_mcp is not available
class MockMCPConfig:
    """Mock configuration class for LinkedIn MCP when the real module is not available."""
    
    def __init__(self, **kwargs):
        """Initialize with any keyword arguments."""
        self.client_id = kwargs.get('client_id', '')
        self.client_secret = kwargs.get('client_secret', '')
        self.redirect_uri = kwargs.get('redirect_uri', '')
        self.session_storage_path = kwargs.get('session_storage_path', './sessions')
        
    def dict(self):
        """Return configuration as dictionary."""
        return {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri,
            'session_storage_path': self.session_storage_path
        }

class MockLinkedInMCP:
    """Mock implementation of LinkedIn MCP class."""
    
    def __init__(self, config):
        self.config = config
        logger.info("Initialized mock LinkedIn MCP client")
        
    async def authenticate(self):
        """Mock authentication method."""
        logger.info("Mock authentication called - always returns False")
        return False
        
    async def search_jobs(self, keywords, location, count=10):
        """Mock job search method."""
        logger.info(f"Mock job search called with keywords: {keywords}, location: {location}")
        return []
        
    async def get_job_description(self, job_id):
        """Mock job description retrieval."""
        logger.info(f"Mock get job description called for job ID: {job_id}")
        return {"description": "This is a mock job description."}
        
    async def apply_to_job(self, job_id, resume_path, cover_letter_path=None):
        """Mock job application."""
        logger.info(f"Mock apply to job called for job ID: {job_id}")
        return False

# Try to import the real linkedin_mcp module
try:
    import importlib
    linkedin_mcp_spec = importlib.util.find_spec("linkedin_mcp")
    if (linkedin_mcp_spec is not None):
        # The module exists, so we can safely import it
        from linkedin_mcp import LinkedInMCP, MCPConfig
        LINKEDIN_MCP_AVAILABLE = True
        logger.info("LinkedIn MCP module imported successfully.")
    else:
        # Module doesn't exist, use our mock classes
        LinkedInMCP = MockLinkedInMCP
        MCPConfig = MockMCPConfig
        logger.warning("LinkedIn MCP module not found. Using mock implementation.")
except ImportError:
    # Import error, use our mock classes
    LinkedInMCP = MockLinkedInMCP
    MCPConfig = MockMCPConfig
    logger.warning("Failed to import LinkedIn MCP. Using mock implementation.")

def create_linkedin_mcp(config_dict: Dict[str, Any]) -> Any:
    """
    Create a LinkedIn MCP instance with the given configuration.
    
    Args:
        config_dict: Dictionary of configuration values
        
    Returns:
        LinkedIn MCP instance (real or mock)
    """
    if LINKEDIN_MCP_AVAILABLE:
        mcp_config = MCPConfig(
            client_id=config_dict.get('client_id', ''),
            client_secret=config_dict.get('client_secret', ''),
            redirect_uri=config_dict.get('redirect_uri', ''),
            session_storage_path=config_dict.get('session_storage_path', './sessions')
        )
        return LinkedInMCP(mcp_config)
    else:
        return MockLinkedInMCP(MockMCPConfig(**config_dict))

def is_linkedin_mcp_available() -> bool:
    """
    Check if the LinkedIn MCP module is available.
    
    Returns:
        True if the module is available, False otherwise
    """
    return LINKEDIN_MCP_AVAILABLE