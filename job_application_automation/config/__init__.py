"""
Configuration module for the job application automation system.
This package contains configuration settings for various components of the system.
"""

# Import all configuration modules for easy access
from .browser_config import BrowserConfig
from .crawl4ai_config import Crawl4AIConfig
from .linkedin_mcp_config import LinkedInMCPConfig
from .llama_config import LlamaConfig
from .config import LLMConfig
from .gemini_config import GeminiConfig
from .logging_config import LoggingConfig

__all__ = [
    'BrowserConfig',
    'Crawl4AIConfig', 
    'LinkedInMCPConfig',
    'LlamaConfig',
    'LLMConfig',
    'GeminiConfig',
    'LoggingConfig'
]

# Set default LLM provider to Gemini
DEFAULT_LLM_PROVIDER = "gemini"