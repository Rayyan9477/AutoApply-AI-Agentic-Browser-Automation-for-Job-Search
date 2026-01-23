"""Configuration settings for LLM integration."""
import os
from typing import Optional
from pydantic import BaseModel, Field, SecretStr
from dotenv import load_dotenv

load_dotenv()

class LlamaConfig(BaseModel):
    use_api: bool = Field(default=os.getenv("LLAMA_USE_API", "true").lower() == "true")
    api_provider: Optional[str] = Field(default=os.getenv("LLAMA_API_PROVIDER", "gemini"))
    api_model: Optional[str] = Field(default=os.getenv("LLAMA_API_MODEL", None))
    github_token: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("GITHUB_TOKEN", "")))
    groq_api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("GROQ_API_KEY", "")))
    gemini_api_key: SecretStr = Field(default_factory=lambda: SecretStr(os.getenv("GEMINI_API_KEY", "")))
    temperature: float = Field(default=float(os.getenv("TEMPERATURE", "0.7")))
    max_tokens: int = Field(default=int(os.getenv("MAX_TOKENS", "4000")))
    
    @classmethod
    def from_env(cls):
        return cls()
