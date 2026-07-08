"""Phase 4 W4: /metrics is open in non-prod but bearer-token-guarded (fail-closed) in prod,
plus the production-config fail-closed guard."""

from unittest.mock import MagicMock

import pytest

from app.config.settings import Environment
from app.main import metrics_authorized, validate_production_settings


def _cfg(env, token=""):
    cfg = MagicMock()
    cfg.environment = env
    cfg.metrics_token.get_secret_value.return_value = token
    return cfg


class TestMetricsAuthorized:
    def test_open_in_non_production(self):
        assert metrics_authorized(_cfg(Environment.DEVELOPMENT), None) is True
        assert metrics_authorized(_cfg(Environment.STAGING), None) is True

    def test_production_requires_matching_token(self):
        cfg = _cfg(Environment.PRODUCTION, token="s3cr3t")
        assert metrics_authorized(cfg, "Bearer s3cr3t") is True
        assert metrics_authorized(cfg, "Bearer wrong") is False
        assert metrics_authorized(cfg, None) is False

    def test_production_fails_closed_when_token_unset(self):
        assert metrics_authorized(_cfg(Environment.PRODUCTION, token=""), "Bearer ") is False


class TestMetricsRoute:
    async def test_metrics_open_in_test_env(self, anon_client):
        r = await anon_client.get("/metrics")
        assert r.status_code == 200
        assert "autoapply" in r.text or "python_info" in r.text  # prometheus exposition


def _prod_cfg(secret="x" * 40, cors=None, provider="s3", url_sign="real-secret"):
    cfg = MagicMock()
    cfg.environment = Environment.PRODUCTION
    cfg.auth.secret_key.get_secret_value.return_value = secret
    cfg.cors_origins = cors if cors is not None else ["https://app.example.com"]
    cfg.storage.provider = provider
    cfg.storage.url_signing_secret.get_secret_value.return_value = url_sign
    return cfg


class TestValidateProductionSettings:
    def test_non_production_skips(self):
        cfg = MagicMock()
        cfg.environment = Environment.DEVELOPMENT
        validate_production_settings(cfg)  # no raise

    def test_valid_production_passes(self):
        validate_production_settings(_prod_cfg())  # no raise

    def test_default_secret_key_fails_closed(self):
        with pytest.raises(RuntimeError, match="AUTH__SECRET_KEY"):
            validate_production_settings(_prod_cfg(secret="dev-insecure-change-me"))

    def test_short_secret_key_fails_closed(self):
        with pytest.raises(RuntimeError, match="AUTH__SECRET_KEY"):
            validate_production_settings(_prod_cfg(secret="short"))

    def test_wildcard_cors_fails_closed(self):
        with pytest.raises(RuntimeError, match="CORS_ORIGINS"):
            validate_production_settings(_prod_cfg(cors=["*"]))

    def test_local_storage_default_signing_secret_fails_closed(self):
        with pytest.raises(RuntimeError, match="URL_SIGNING_SECRET"):
            validate_production_settings(
                _prod_cfg(provider="local", url_sign="dev-insecure-change-me")
            )
