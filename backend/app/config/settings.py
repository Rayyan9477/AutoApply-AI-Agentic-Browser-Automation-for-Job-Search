"""Application settings loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ApplyMode(StrEnum):
    """Job application submission mode."""

    AUTONOMOUS = "autonomous"
    REVIEW = "review"
    BATCH = "batch"


class Environment(StrEnum):
    """Application environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LLMSettings(BaseSettings):
    """LLM provider configuration."""

    model_config = SettingsConfigDict(env_prefix="LLM__")

    portkey_api_key: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    gemini_api_key: SecretStr = SecretStr("")
    openrouter_api_key: SecretStr = SecretStr("")
    github_token: SecretStr = SecretStr("")
    preferred_provider: str = "openai"
    fallback_providers: list[str] = ["groq", "openrouter"]
    default_model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    # AWS Bedrock: platform-authenticated via the standard AWS credential chain (env vars,
    # ~/.aws, or an instance/role) — no per-user key. Use a ``bedrock/<model-id>`` default_model
    # (e.g. ``bedrock/anthropic.claude-sonnet-4-5-20250929-v1:0``) to route through Bedrock.
    bedrock_region: str = "us-east-1"

    @field_validator("temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Clamp temperature to valid range."""
        return max(0.0, min(2.0, v))

    @field_validator("max_tokens")
    @classmethod
    def validate_max_tokens(cls, v: int) -> int:
        """Ensure max_tokens is positive."""
        return max(1, v)


class BrowserSettings(BaseSettings):
    """Browser automation configuration."""

    model_config = SettingsConfigDict(env_prefix="BROWSER__")

    headless: bool = True
    max_parallel: int = 3
    user_data_dir: str = "./data/sessions/chrome_profile"
    keep_alive: bool = True
    max_steps: int = 50
    max_failures: int = 3
    step_timeout: int = 120
    use_vision: str = "auto"
    # When False (default), the worker uses a placeholder submit so the loop is
    # demoable/CI-safe. Set True (with a real browser + assisted-login session) to drive
    # the live browser-use apply (run_apply).
    live_apply: bool = False

    @field_validator("max_parallel")
    @classmethod
    def validate_max_parallel(cls, v: int) -> int:
        """Clamp parallelism to 1-5 range."""
        return max(1, min(5, v))


class AuthSettings(BaseSettings):
    """Authentication / JWT configuration."""

    model_config = SettingsConfigDict(env_prefix="AUTH__")

    secret_key: SecretStr = SecretStr("dev-insecure-change-me")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30
    ws_ticket_expire_seconds: int = 60


class EmailSettings(BaseSettings):
    """Transactional email (password reset). Defaults to the ``log`` provider, which writes the
    would-be email to the logs so the flow is fully functional in dev/CI without a mail server.
    Set ``provider=smtp`` plus the SMTP fields (or point at SES/Mailgun SMTP) for real delivery.
    """

    model_config = SettingsConfigDict(env_prefix="EMAIL__")

    provider: str = "log"  # "log" (dev/CI) | "smtp"
    from_address: str = "no-reply@autoapply.ai"
    from_name: str = "AutoApply AI"
    # Frontend origin used to build the reset link the user clicks.
    frontend_base_url: str = "http://localhost:5173"
    reset_token_expire_minutes: int = 30

    # SMTP transport (used when provider == "smtp").
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: SecretStr = SecretStr("")
    smtp_starttls: bool = True


class SecretsSettings(BaseSettings):
    """Envelope-encryption configuration for per-user secrets (BYO-key)."""

    model_config = SettingsConfigDict(env_prefix="SECRETS__")

    provider: str = "local"
    # Comma-separated Fernet keys; the first is the current KEK. If empty outside
    # production, an ephemeral dev key is generated at runtime.
    app_keys: str = ""


class StorageSettings(BaseSettings):
    """File storage configuration (local FS or any S3-compatible store: AWS S3, R2, B2, MinIO)."""

    model_config = SettingsConfigDict(env_prefix="STORAGE__")

    provider: str = "local"
    local_root: str = "./data/storage"
    url_signing_secret: SecretStr = SecretStr("dev-insecure-change-me")
    url_default_expiry: int = 300

    # S3-compatible settings (used when provider == "s3").
    bucket: str = ""
    region: str = ""
    endpoint_url: str = ""  # e.g. https://<account>.r2.cloudflarestorage.com for Cloudflare R2
    access_key_id: SecretStr = SecretStr("")
    secret_access_key: SecretStr = SecretStr("")


class Settings(BaseSettings):
    """Root application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///data/db/autoapply.db"
    redis_url: str = "redis://localhost:6379/0"

    # Application behavior
    apply_mode: ApplyMode = ApplyMode.REVIEW
    min_ats_score: float = 0.75
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = "INFO"
    # Bearer token required to scrape /metrics in production (fail-closed if unset there).
    metrics_token: SecretStr = SecretStr("")
    # Optional error tracking. When set, Sentry captures unhandled API + worker exceptions.
    sentry_dsn: SecretStr = SecretStr("")

    # Nested settings
    llm: LLMSettings = LLMSettings()
    browser: BrowserSettings = BrowserSettings()
    auth: AuthSettings = AuthSettings()
    secrets: SecretsSettings = SecretsSettings()
    storage: StorageSettings = StorageSettings()
    email: EmailSettings = EmailSettings()

    # Job discovery
    exa_api_key: SecretStr = SecretStr("")

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @field_validator("min_ats_score")
    @classmethod
    def validate_min_ats_score(cls, v: float) -> float:
        """Clamp ATS score threshold to 0-1 range."""
        return max(0.0, min(1.0, v))

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Normalize log level to uppercase."""
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached application settings singleton."""
    return Settings()
