"""
Centralized configuration management for the job application automation system.
This module provides a unified way to handle configuration with validation,
environment variable support, and secure credential handling.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Type, TypeVar, get_type_hints
from pydantic import BaseModel, Field, validator, SecretStr
import dotenv

# Load environment variables from .env file if present
dotenv.load_dotenv()

# Logger for configuration operations
logger = logging.getLogger(__name__)

# Project root for absolute paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Import unified BrowserConfig from browser_config module
from job_application_automation.config.browser_config import BrowserConfig

class LoggingConfig(BaseModel):
    """Configuration for logging."""
    level: str = Field(default="INFO", description="Logging level")
    file_path: str = Field(default_factory=lambda: str(_PROJECT_ROOT / "data" / "logs" / "application.log"), description="Log file path")
    log_dir: str = Field(default_factory=lambda: str(_PROJECT_ROOT / "data" / "logs"), description="Directory for log files")
    format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log message format"
    )
    log_format: str = Field(
        default="standard", 
        description="Log format type (standard or json)"
    )
    console_logging: bool = Field(default=True, description="Enable console logging")
    file_logging: bool = Field(default=True, description="Enable file logging")
    max_file_size: int = Field(default=10485760, description="Maximum log file size in bytes")
    max_size_mb: int = Field(default=10, description="Maximum log file size in MB")
    backup_count: int = Field(default=5, description="Number of backup log files to keep")
    
    @validator('level')
    def validate_level(cls, v):
        """Validate logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            logger.warning(f"Invalid logging level: {v}. Using default: INFO")
            return "INFO"
        return v.upper()
    
    @validator('log_format')
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ['standard', 'json']
        if v.lower() not in valid_formats:
            logger.warning(f"Invalid log format: {v}. Using default: standard")
            return "standard"
        return v.lower()

class LinkedInConfig(BaseModel):
    """Configuration for LinkedIn integration."""
    client_id: SecretStr = Field(default=SecretStr(""), description="LinkedIn API client ID")
    client_secret: SecretStr = Field(default=SecretStr(""), description="LinkedIn API client secret")
    redirect_uri: str = Field(
        default="http://localhost:8000/callback", 
        description="OAuth redirect URI"
    )
    session_path: str = Field(default_factory=lambda: str(_PROJECT_ROOT / "data" / "sessions"), description="Path to store session data")
    session_storage_path: str = Field(default_factory=lambda: str(_PROJECT_ROOT / "data" / "sessions"), description="Path to store session data (compat)")
    use_api: bool = Field(default=True, description="Whether to use LinkedIn API")
    use_mcp: bool = Field(default=True, description="Whether to use LinkedIn MCP")
    
    class Config:
        """Pydantic configuration."""
        # These fields contain sensitive information
        sensitive_fields = {'client_id', 'client_secret'}

class CrawlConfig(BaseModel):
    """Configuration for web crawling."""
    rate_limit: float = Field(
        default=1.0, 
        description="Minimum time between requests in seconds"
    )
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    user_agent: str = Field(
        default="Mozilla/5.0 Job Application Automation Bot",
        description="User agent string to use for requests"
    )
    
    @validator('rate_limit')
    def validate_rate_limit(cls, v):
        """Validate rate limit."""
        if v < 0:
            logger.warning(f"Invalid rate limit: {v}. Using default: 1.0")
            return 1.0
        return v

class LLMConfig(BaseModel):
    """Configuration for LLM services."""
    provider: str = Field(default="gemini", description="LLM provider (gemini, openai, etc.)")
    api_key: SecretStr = Field(default=SecretStr(""), description="API key for LLM service")
    model: str = Field(default="gemini-pro", description="Model to use")
    temperature: float = Field(default=0.7, description="Temperature for generation (0-1)")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")
    top_p: float = Field(default=0.95, description="Nucleus sampling parameter (0-1)")
    top_k: int = Field(default=40, description="Top-k sampling parameter")
    
    # Gemini-specific settings
    safety_settings: Dict[str, str] = Field(
        default_factory=lambda: {
            "HARM_CATEGORY_HARASSMENT": "BLOCK_NONE",
            "HARM_CATEGORY_HATE_SPEECH": "BLOCK_NONE",
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": "BLOCK_NONE",
            "HARM_CATEGORY_DANGEROUS_CONTENT": "BLOCK_NONE"
        },
        description="Safety settings for Gemini model"
    )
    
    # Provider-specific settings
    openai_model: str = Field(default="gpt-4", description="OpenAI model to use")
    gemini_model: str = Field(default="gemini-pro", description="Gemini model to use")
    
    # API configuration
    use_api: bool = Field(default=True, description="Whether to use API for LLM integration")
    api_base_url: Optional[str] = Field(
        default="https://generativelanguage.googleapis.com/v1beta",
        description="Base URL for API"
    )
    
    @validator('temperature')
    def validate_temperature(cls, v):
        """Validate temperature is between 0 and 1."""
        if not 0 <= v <= 1:
            logger.warning(f"Temperature {v} is outside recommended range [0, 1]. Clamping to nearest valid value.")
            return max(0, min(1, v))
        return v
        
    @validator('top_p')
    def validate_top_p(cls, v):
        """Validate top_p is between 0 and 1."""
        if not 0 <= v <= 1:
            logger.warning(f"top_p {v} is outside valid range [0, 1]. Clamping to nearest valid value.")
            return max(0, min(1, v))
        return v
        
    @validator('top_k')
    def validate_top_k(cls, v):
        """Validate top_k is at least 1."""
        if v < 1:
            logger.warning(f"top_k must be at least 1, got {v}. Setting to 1.")
            return 1
        return v
    
    class Config:
        """Pydantic configuration."""
        # These fields contain sensitive information
        sensitive_fields = {'api_key'}

class SecurityConfig(BaseModel):
    """Security-related configuration."""
    encrypt_sensitive_data: bool = Field(default=True, description="Encrypt sensitive data in storage")
    encryption_key_path: Optional[str] = Field(
        default=None, 
        description="Path to encryption key file"
    )
    use_keyring: bool = Field(
        default=True, 
        description="Use system keyring for storing sensitive data"
    )
    secure_delete: bool = Field(
        default=True, 
        description="Securely delete sensitive files on cleanup"
    )

class ApplicationConfig(BaseModel):
    """Main application configuration."""
    # Component configurations
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    linkedin: LinkedInConfig = Field(default_factory=LinkedInConfig)
    crawl: CrawlConfig = Field(default_factory=CrawlConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # Application settings
    data_dir: str = Field(default_factory=lambda: str(_PROJECT_ROOT / "data"), description="Directory for application data")
    min_match_score: float = Field(
        default=0.7, 
        description="Minimum score to consider a job a match"
    )
    max_applications_per_run: int = Field(
        default=5, 
        description="Maximum applications to submit in one run"
    )
    
    @validator('min_match_score')
    def validate_min_match_score(cls, v):
        """Validate minimum match score."""
        if v < 0 or v > 1:
            logger.warning(f"Invalid min_match_score: {v}. Using default: 0.7")
            return 0.7
        return v

class ConfigManager:
    """
    Manages application configuration with support for file-based config,
    environment variables, and secure secrets storage.
    """
    
    ENV_PREFIX = "JOB_APP_"
    
    def __init__(
        self, 
        config_path: Path = _PROJECT_ROOT / "config" / "config.yaml",
        secrets_path: Path = _PROJECT_ROOT / "config" / ".secrets.yaml"
    ):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the main configuration file
            secrets_path: Path to the secrets file (should be gitignored)
        """
        self.config_path = Path(config_path)
        self.secrets_path = Path(secrets_path)
        
        # Create parent directories if they don't exist
        if not self.config_path.parent.exists():
            self.config_path.parent.mkdir(parents=True)
        
        # Load or create config
        self.config_data = self._load_config()
        self.secrets_data = self._load_secrets()
        
        # Create config object
        self.config = self._create_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file or create default if it doesn't exist.
        
        Returns:
            Dictionary containing configuration data
        """
        if not self.config_path.exists():
            logger.info(f"Creating default configuration at {self.config_path}")
            # Create default config
            default_config = ApplicationConfig().dict()
            
            # Filter out sensitive data
            filtered_config = self._filter_sensitive_data(default_config)
            
            # Save default config
            with open(self.config_path, 'w') as f:
                yaml.dump(filtered_config, f, default_flow_style=False)
            
            return filtered_config
        
        try:
            # Load existing config
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            return {}
    
    def _load_secrets(self) -> Dict[str, Any]:
        """
        Load secrets from file or create empty if it doesn't exist.
        
        Returns:
            Dictionary containing secrets data
        """
        if not self.secrets_path.exists():
            logger.info(f"Creating empty secrets file at {self.secrets_path}")
            
            # Extract sensitive fields from default config
            default_config = ApplicationConfig().dict()
            secrets = self._extract_sensitive_data(default_config)
            
            # Save empty secrets file
            with open(self.secrets_path, 'w') as f:
                yaml.dump(secrets, f, default_flow_style=False)
            
            # Set secure permissions (unix-like systems)
            if os.name != 'nt':  # Not Windows
                try:
                    os.chmod(self.secrets_path, 0o600)  # Owner read/write only
                except Exception as e:
                    logger.warning(f"Could not set secure permissions on secrets file: {e}")
            
            return secrets
        
        try:
            # Load existing secrets
            with open(self.secrets_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Error loading secrets: {e}")
            return {}
    
    def _filter_sensitive_data(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out sensitive data from configuration.
        
        Args:
            config_data: Configuration data dictionary
            
        Returns:
            Configuration with sensitive data removed
        """
        filtered_data = {}
        
        # Process each key in the config dictionary
        for key, value in config_data.items():
            if isinstance(value, dict):
                # Recursively filter nested dictionaries
                filtered_data[key] = self._filter_sensitive_data(value)
            elif isinstance(value, (str, int, float, bool, list, tuple)) or value is None:
                # Keep non-sensitive data types
                filtered_data[key] = value
            elif hasattr(value, "get_secret_value"):
                # This is a SecretStr, don't include the value
                filtered_data[key] = "***"
        
        return filtered_data
    
    def _extract_sensitive_data(self, config_data: Dict[str, Any], path: str = "") -> Dict[str, Any]:
        """
        Extract sensitive data from configuration.
        
        Args:
            config_data: Configuration data dictionary
            path: Current path in the configuration (for nested dictionaries)
            
        Returns:
            Dictionary with sensitive data
        """
        sensitive_data = {}
        
        # Process each key in the config dictionary
        for key, value in config_data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, dict):
                # Recursively extract from nested dictionaries
                nested_data = self._extract_sensitive_data(value, current_path)
                if nested_data:
                    sensitive_data.update(nested_data)
            elif hasattr(value, "get_secret_value"):
                # This is a SecretStr, extract the value
                sensitive_data[current_path] = value.get_secret_value()
        
        return sensitive_data
    
    def _apply_environment_variables(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override configuration with values from environment variables.
        
        Environment variables should be prefixed with ENV_PREFIX and use double underscores
        for nested keys, e.g., JOB_APP_LINKEDIN__CLIENT_ID
        
        Args:
            config_data: Configuration data dictionary
            
        Returns:
            Configuration with environment variable overrides applied
        """
        result = config_data.copy()
        
        # Look for environment variables with the proper prefix
        for env_var, value in os.environ.items():
            if (env_var.startswith(self.ENV_PREFIX)):
                # Remove prefix and split by double underscore
                key_path = env_var[len(self.ENV_PREFIX):].split('__')
                
                # Navigate to the proper location in the config
                current = result
                for i, key in enumerate(key_path):
                    key = key.lower()  # Case insensitive
                    
                    if i == len(key_path) - 1:
                        # Last element, set the value
                        # Try to convert to appropriate type
                        if value.lower() == 'true':
                            current[key] = True
                        elif value.lower() == 'false':
                            current[key] = False
                        elif value.isdigit():
                            current[key] = int(value)
                        elif '.' in value and all(p.isdigit() for p in value.split('.', 1)):
                            current[key] = float(value)
                        else:
                            current[key] = value
                    else:
                        # Not the last element, ensure the key exists
                        if key not in current or not isinstance(current[key], dict):
                            current[key] = {}
                        current = current[key]
        
        return result
    
    def _merge_configs(self, config: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge configuration and secrets into a single dictionary.
        
        Args:
            config: Main configuration dictionary
            secrets: Secrets dictionary with dot-separated keys
            
        Returns:
            Merged configuration dictionary
        """
        result = config.copy()
        
        # Apply each secret
        for key_path, value in secrets.items():
            keys = key_path.split('.')
            
            # Navigate to the proper location
            current = result
            for i, key in enumerate(keys):
                if i == len(keys) - 1:
                    # Last element, set the value
                    current[key] = value
                else:
                    # Ensure the key exists
                    if key not in current:
                        current[key] = {}
                    current = current[key]
        
        return result
    
    def _create_config(self) -> ApplicationConfig:
        """
        Create configuration object from loaded data.
        
        Returns:
            ApplicationConfig object
        """
        # Apply environment variable overrides
        config_with_env = self._apply_environment_variables(self.config_data)
        
        # Merge with secrets
        merged_config = self._merge_configs(config_with_env, self.secrets_data)
        
        # Create object
        try:
            return ApplicationConfig(**merged_config)
        except Exception as e:
            logger.error(f"Error creating configuration: {e}")
            # Fall back to defaults
            return ApplicationConfig()
    
    def get_config(self) -> ApplicationConfig:
        """
        Get the current configuration.
        
        Returns:
            ApplicationConfig object
        """
        return self.config
    
    def update_config(self, **kwargs) -> None:
        """
        Update configuration with new values.
        
        Args:
            **kwargs: Keys and values to update (can use dot notation for nested keys)
        """
        # For each key-value pair
        for key, value in kwargs.items():
            if '.' in key:
                # Nested key
                keys = key.split('.')
                current = self.config_data
                
                # Navigate to the proper location
                for i, k in enumerate(keys):
                    if i == len(keys) - 1:
                        # Last element, set the value
                        current[k] = value
                    else:
                        # Ensure the key exists
                        if k not in current:
                            current[k] = {}
                        current = current[k]
            else:
                # Top-level key
                self.config_data[key] = value
        
        # Recreate config object
        self.config = self._create_config()
    
    def save_config(self) -> bool:
        """
        Save current configuration to file.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Filter out sensitive data
            filtered_config = self._filter_sensitive_data(self.config.dict())
            
            # Save to file
            with open(self.config_path, 'w') as f:
                yaml.dump(filtered_config, f, default_flow_style=False)
            
            return True
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")
            return False
    
    def update_secret(self, key: str, value: str) -> bool:
        """
        Update a secret value.
        
        Args:
            key: Secret key (can use dot notation for nested keys)
            value: Secret value
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Add to secrets
            self.secrets_data[key] = value
            
            # Save to file
            with open(self.secrets_path, 'w') as f:
                yaml.dump(self.secrets_data, f, default_flow_style=False)
            
            # Recreate config object
            self.config = self._create_config()
            
            return True
        except Exception as e:
            logger.error(f"Error updating secret: {e}")
            return False

# Create a global instance of the config manager
_config_manager = None

def get_config_manager() -> ConfigManager:
    """
    Get the global configuration manager instance.
    
    Returns:
        ConfigManager instance
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config() -> ApplicationConfig:
    """
    Get the current application configuration.
    
    Returns:
        ApplicationConfig object
    """
    return get_config_manager().get_config()