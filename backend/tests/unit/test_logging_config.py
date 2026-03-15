"""Unit tests for app.observability.logging.configure_logging."""

from __future__ import annotations

import logging

from app.observability.logging import configure_logging


class TestConfigureLogging:
    def test_development_does_not_raise(self):
        configure_logging("DEBUG", "development")

    def test_production_does_not_raise(self):
        configure_logging("INFO", "production")

    def test_sets_root_log_level(self):
        configure_logging("WARNING", "development")
        root = logging.getLogger()
        assert root.level == logging.WARNING

    def test_sets_debug_level(self):
        configure_logging("DEBUG", "development")
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_noisy_loggers_suppressed(self):
        configure_logging("DEBUG", "development")
        for name in ("uvicorn.access", "httpx", "httpcore", "sqlalchemy.engine"):
            assert logging.getLogger(name).level >= logging.WARNING

    def test_handler_attached_to_root(self):
        configure_logging("INFO", "production")
        root = logging.getLogger()
        assert len(root.handlers) >= 1

    def test_invalid_level_defaults_to_info(self):
        configure_logging("NONEXISTENT_LEVEL", "development")
        root = logging.getLogger()
        assert root.level == logging.INFO
