"""
Unit tests for the configuration system.
"""
import os
import pytest
from pathlib import Path
import tempfile
import yaml
from typing import Dict, Any

from job_application_automation.config.config import ConfigManager, ApplicationConfig, LinkedInConfig, BrowserConfig

class TestConfigManager:
    """Tests for the ConfigManager class."""
    
    def test_default_config_creation(self):
        """Test that default configuration is created properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary config path
            temp_config_path = Path(temp_dir) / "config.yaml"
            temp_secrets_path = Path(temp_dir) / ".secrets.yaml"
            
            # Initialize config manager with temporary paths
            config_manager = ConfigManager(temp_config_path, temp_secrets_path)
            
            # Get config and check it's the right type
            config = config_manager.get_config()
            assert isinstance(config, ApplicationConfig)
            
            # Check default values
            assert config.browser.headless is True
            assert config.min_match_score == 0.7
            assert config.linkedin.redirect_uri == "http://localhost:8000/callback"
            
            # Check that config file was created
            assert temp_config_path.exists()
    
    def test_config_from_dict(self):
        """Test loading configuration from a dictionary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary config path
            temp_config_path = Path(temp_dir) / "config.yaml"
            
            # Create config file with custom values
            config_data = {
                "browser": {
                    "headless": False,
                    "browser_type": "firefox"
                },
                "min_match_score": 0.8,
                "linkedin": {
                    "redirect_uri": "http://localhost:9000/callback"
                }
            }
            
            # Write config to file
            with open(temp_config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Initialize config manager with the temporary config path
            config_manager = ConfigManager(temp_config_path)
            
            # Get config and verify custom values
            config = config_manager.get_config()
            assert config.browser.headless is False
            assert config.browser.browser_type == "firefox"
            assert config.min_match_score == 0.8
            assert config.linkedin.redirect_uri == "http://localhost:9000/callback"
    
    def test_environment_variable_override(self, monkeypatch):
        """Test that environment variables override configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary config path
            temp_config_path = Path(temp_dir) / "config.yaml"
            
            # Set environment variables
            monkeypatch.setenv("JOB_APP_BROWSER__HEADLESS", "False")
            monkeypatch.setenv("JOB_APP_MIN_MATCH_SCORE", "0.9")
            
            # Initialize config manager
            config_manager = ConfigManager(temp_config_path)
            
            # Get config and verify values from environment variables
            config = config_manager.get_config()
            assert config.browser.headless is False
            assert config.min_match_score == 0.9
    
    def test_config_validation(self):
        """Test that configuration validation works."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary config path
            temp_config_path = Path(temp_dir) / "config.yaml"
            
            # Create config file with invalid values
            config_data = {
                "browser": {
                    "browser_type": "invalid_browser"  # Invalid browser type
                },
                "min_match_score": 2.0  # Outside valid range 0-1
            }
            
            # Write config to file
            with open(temp_config_path, 'w') as f:
                yaml.dump(config_data, f)
            
            # Initialize config manager - it should fall back to defaults
            config_manager = ConfigManager(temp_config_path)
            
            # Get config and verify default values are used instead of invalid ones
            config = config_manager.get_config()
            assert config.browser.browser_type == "chromium"  # default value
            assert config.min_match_score == 0.7  # default value
    
    def test_update_config(self):
        """Test updating configuration values."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create a temporary config path
            temp_config_path = Path(temp_dir) / "config.yaml"
            
            # Initialize config manager
            config_manager = ConfigManager(temp_config_path)
            
            # Update values
            config_manager.update_config(**{
                "browser.headless": False,
                "min_match_score": 0.8
            })
            
            # Get config and verify updated values
            config = config_manager.get_config()
            assert config.browser.headless is False
            assert config.min_match_score == 0.8
            
            # Save and reload config
            config_manager.save_config()
            new_config_manager = ConfigManager(temp_config_path)
            new_config = new_config_manager.get_config()
            
            # Verify values persist after reload
            assert new_config.browser.headless is False
            assert new_config.min_match_score == 0.8