"""Tests for application settings configuration."""



from app.config.settings import ApplyMode, BrowserSettings, Environment, LLMSettings, Settings


class TestSettings:
    """Test Settings loading and validation."""

    def test_default_settings_load_without_env(self) -> None:
        """Default settings should load without any env vars set."""
        settings = Settings(
            _env_file=None,  # Don't load .env file in tests
        )
        assert settings.apply_mode == ApplyMode.REVIEW
        assert settings.min_ats_score == 0.75
        assert settings.environment == Environment.DEVELOPMENT
        assert settings.log_level == "INFO"

    def test_min_ats_score_clamped_to_valid_range(self) -> None:
        """ATS score threshold should be clamped to 0-1."""
        settings = Settings(_env_file=None, min_ats_score=1.5)
        assert settings.min_ats_score == 1.0

        settings = Settings(_env_file=None, min_ats_score=-0.5)
        assert settings.min_ats_score == 0.0

    def test_log_level_normalized_to_uppercase(self) -> None:
        """Log level should be normalized to uppercase."""
        settings = Settings(_env_file=None, log_level="debug")
        assert settings.log_level == "DEBUG"

    def test_apply_mode_enum_values(self) -> None:
        """ApplyMode enum should have exactly 3 values."""
        assert ApplyMode.AUTONOMOUS.value == "autonomous"
        assert ApplyMode.REVIEW.value == "review"
        assert ApplyMode.BATCH.value == "batch"


class TestLLMSettings:
    """Test LLM settings validation."""

    def test_temperature_clamped_to_valid_range(self) -> None:
        """Temperature should be clamped to 0-2."""
        settings = LLMSettings(temperature=3.0)
        assert settings.temperature == 2.0

        settings = LLMSettings(temperature=-1.0)
        assert settings.temperature == 0.0

    def test_max_tokens_must_be_positive(self) -> None:
        """Max tokens should be at least 1."""
        settings = LLMSettings(max_tokens=0)
        assert settings.max_tokens == 1

    def test_default_provider_is_openai(self) -> None:
        """Default preferred provider should be openai."""
        settings = LLMSettings()
        assert settings.preferred_provider == "openai"


class TestBrowserSettings:
    """Test browser settings validation."""

    def test_max_parallel_clamped_to_valid_range(self) -> None:
        """Max parallel sessions should be clamped to 1-5."""
        settings = BrowserSettings(max_parallel=10)
        assert settings.max_parallel == 5

        settings = BrowserSettings(max_parallel=0)
        assert settings.max_parallel == 1

    def test_default_headless_is_true(self) -> None:
        """Browser should default to headless mode."""
        settings = BrowserSettings()
        assert settings.headless is True
