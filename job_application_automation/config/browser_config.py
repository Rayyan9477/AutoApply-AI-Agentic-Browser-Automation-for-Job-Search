"""
Configuration settings for browser automation.
"""
import os
from pathlib import Path
from typing import Optional, Dict
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

_BROWSER_CONFIG_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv()


class BrowserConfig(BaseModel):
    """Configuration for browser automation."""
    
    # Browser settings
    browser_type: str = Field(
        default=os.getenv("BROWSER_TYPE", "chromium"),
        description="Browser type to use (chromium, firefox, webkit)"
    )
    headless: bool = Field(
        default=os.getenv("HEADLESS", "true").lower() == "true",
        description="Run browser in headless mode"
    )
    
    # User data directory
    user_data_dir: Optional[str] = Field(
        default=os.getenv("BROWSER_USER_DATA_DIR", None),
        description="Path to browser user data directory for persistent sessions"
    )
    
    # Window settings
    window_size: Dict[str, int] = Field(
        default_factory=lambda: {
            "width": int(os.getenv("BROWSER_WIDTH", "1920")),
            "height": int(os.getenv("BROWSER_HEIGHT", "1080"))
        },
        description="Browser window size"
    )
    
    # Timeout settings
    timeout: int = Field(
        default=int(os.getenv("BROWSER_TIMEOUT", "30000")),
        description="Default timeout in milliseconds"
    )
    page_load_timeout: int = Field(
        default=int(os.getenv("PAGE_LOAD_TIMEOUT", "60000")),
        description="Page load timeout in milliseconds"
    )
    
    # LinkedIn-specific settings
    linkedin_manual_login: bool = Field(
        default=os.getenv("LINKEDIN_MANUAL_LOGIN", "false").lower() == "true",
        description="Whether to use manual login for LinkedIn"
    )
    
    # Chrome-specific settings
    chrome_executable_path: Optional[str] = Field(
        default=os.getenv("CHROME_PATH", None),
        description="Path to Chrome/Chromium executable"
    )
    chrome_driver_path: Optional[str] = Field(
        default=os.getenv("CHROME_DRIVER_PATH", None),
        description="Path to ChromeDriver executable"
    )
    
    # Browser arguments
    browser_args: list = Field(
        default_factory=lambda: [
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
        ],
        description="Additional browser arguments"
    )
    
    # User agent
    user_agent: Optional[str] = Field(
        default=os.getenv("USER_AGENT", None),
        description="Custom user agent string"
    )
    
    # Session management
    save_session: bool = Field(
        default=os.getenv("SAVE_SESSION", "true").lower() == "true",
        description="Save browser session for reuse"
    )
    session_dir: str = Field(
        default=os.getenv("SESSION_DIR", str(_BROWSER_CONFIG_ROOT / "data" / "sessions")),
        description="Directory to store browser sessions"
    )
    
    # Anti-detection settings
    stealth_mode: bool = Field(
        default=os.getenv("STEALTH_MODE", "true").lower() == "true",
        description="Enable stealth mode to avoid detection"
    )
    randomize_timing: bool = Field(
        default=os.getenv("RANDOMIZE_TIMING", "true").lower() == "true",
        description="Randomize timing between actions"
    )
    min_delay: float = Field(
        default=float(os.getenv("MIN_DELAY", "1.0")),
        description="Minimum delay between actions in seconds"
    )
    max_delay: float = Field(
        default=float(os.getenv("MAX_DELAY", "3.0")),
        description="Maximum delay between actions in seconds"
    )

    # Screenshots directory
    screenshots_dir: str = Field(
        default=os.getenv("SCREENSHOTS_DIR", "data/screenshots"),
        description="Directory to store browser screenshots"
    )

    # Aliases for backward compatibility
    default_navigation_timeout: int = Field(
        default=int(os.getenv("DEFAULT_NAVIGATION_TIMEOUT", "30000")),
        description="Default navigation timeout in milliseconds"
    )
    default_timeout: int = Field(
        default=int(os.getenv("DEFAULT_TIMEOUT", "30000")),
        description="Default timeout in milliseconds (alias for timeout)"
    )

    @validator('browser_type')
    def validate_browser_type(cls, v):
        """Validate browser type."""
        valid_types = ['chromium', 'firefox', 'webkit', 'chrome']
        if v.lower() not in valid_types:
            raise ValueError(f"Invalid browser type: {v}. Must be one of {valid_types}")
        return v.lower()
    
    @validator('window_size')
    def validate_window_size(cls, v):
        """Validate window size has required keys."""
        if 'width' not in v or 'height' not in v:
            raise ValueError("window_size must have 'width' and 'height' keys")
        if v['width'] < 800 or v['height'] < 600:
            raise ValueError("Window size must be at least 800x600")
        return v
    
    @classmethod
    def from_env(cls) -> "BrowserConfig":
        """Create configuration from environment variables."""
        return cls()
    
    def get_browser_args(self) -> list:
        """Get browser arguments including headless if enabled."""
        args = self.browser_args.copy()
        if self.headless:
            args.append("--headless")
        return args
    
    def get_viewport_size(self) -> Dict[str, int]:
        """Get viewport size from window size."""
        return {
            "width": self.window_size["width"],
            "height": self.window_size["height"]
        }
