"""Configuration settings for LinkedIn MCP integration."""
import os
from pathlib import Path
from pydantic import BaseModel, Field, SecretStr
from dotenv import load_dotenv

load_dotenv()

_MCP_CONFIG_ROOT = Path(__file__).resolve().parent.parent

class LinkedInMCPConfig(BaseModel):
    client_id: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("LINKEDIN_CLIENT_ID", "")))
    client_secret: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("LINKEDIN_CLIENT_SECRET", "")))
    use_mcp: bool = Field(default=os.getenv("USE_LINKEDIN_MCP", "true").lower() == "true")
    session_path: str = Field(default=os.getenv("LINKEDIN_SESSION_PATH", str(_MCP_CONFIG_ROOT / "data" / "sessions")))
    
    @classmethod
    def from_env(cls):
        return cls()
