"""Configuration settings for LinkedIn MCP integration."""
import os
from pydantic import BaseModel, Field, SecretStr
from dotenv import load_dotenv

load_dotenv()

class LinkedInMCPConfig(BaseModel):
    client_id: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("LINKEDIN_CLIENT_ID", "")))
    client_secret: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("LINKEDIN_CLIENT_SECRET", "")))
    use_mcp: bool = Field(default=os.getenv("USE_LINKEDIN_MCP", "true").lower() == "true")
    session_path: str = Field(default=os.getenv("LINKEDIN_SESSION_PATH", "../data/sessions"))
    
    @classmethod
    def from_env(cls):
        return cls()
