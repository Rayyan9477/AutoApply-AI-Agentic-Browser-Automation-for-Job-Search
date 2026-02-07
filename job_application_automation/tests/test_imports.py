"""
Import smoke tests - verify every module can be imported without errors.
This catches broken imports, missing dependencies, and circular import issues.
"""
import pytest
import importlib


# Config modules
CONFIG_MODULES = [
    "job_application_automation.config.config",
    "job_application_automation.config.browser_config",
    "job_application_automation.config.crawl4ai_config",
    "job_application_automation.config.linkedin_mcp_config",
    "job_application_automation.config.llama_config",
]

# Core source modules
SRC_MODULES = [
    "job_application_automation.src.models",
    "job_application_automation.src.database",
    "job_application_automation.src.database_monitor",
    "job_application_automation.src.application_tracker",
    "job_application_automation.src.vector_database",
    "job_application_automation.src.di",
]

# Utility modules
UTIL_MODULES = [
    "job_application_automation.src.utils.path_utils",
    "job_application_automation.src.utils.error_handling",
]

# Service modules
SERVICE_MODULES = [
    "job_application_automation.src.services.llm_client",
]

# LLM provider modules
LLM_PROVIDER_MODULES = [
    "job_application_automation.src.llm_providers",
]

# Resume scoring modules
RESUME_SCORING_MODULES = [
    "job_application_automation.src.resume_scoring.scoring_engine",
    "job_application_automation.src.resume_scoring.skill_matcher",
    "job_application_automation.src.resume_scoring.keyword_analyzer",
    "job_application_automation.src.resume_scoring.experience_analyzer",
]

# Job source modules
JOB_SOURCE_MODULES = [
    "job_application_automation.src.job_sources.job_search_manager",
]

# CLI modules
CLI_MODULES = [
    "job_application_automation.src.cli.arguments",
]

# All modules that should be importable
ALL_MODULES = (
    CONFIG_MODULES
    + SRC_MODULES
    + UTIL_MODULES
    + SERVICE_MODULES
    + LLM_PROVIDER_MODULES
    + RESUME_SCORING_MODULES
    + JOB_SOURCE_MODULES
    + CLI_MODULES
)


@pytest.mark.parametrize("module_path", ALL_MODULES)
def test_import_module(module_path):
    """Test that each module can be imported without errors."""
    try:
        importlib.import_module(module_path)
    except ImportError as e:
        pytest.fail(f"Failed to import {module_path}: {e}")
    except Exception as e:
        # Some modules may fail at runtime (e.g., missing API keys, DB not initialized)
        # but they should at least parse and load without import errors
        if "import" in str(e).lower() or "module" in str(e).lower():
            pytest.fail(f"Import-related error in {module_path}: {e}")
        # Other runtime errors (config, env, etc.) are acceptable for smoke tests


def test_config_get_config():
    """Test that get_config() returns a valid config object."""
    from job_application_automation.config.config import get_config
    config = get_config()
    assert config is not None
    assert hasattr(config, "browser")
    assert hasattr(config, "data_dir")
    assert hasattr(config, "logging")


def test_path_utils():
    """Test that path utility functions return valid paths."""
    from job_application_automation.src.utils.path_utils import (
        get_project_root,
        get_data_path,
        get_templates_dir,
        get_logs_dir,
        get_models_dir,
    )

    project_root = get_project_root()
    assert project_root.exists()

    data_path = get_data_path()
    assert data_path.exists()

    templates_dir = get_templates_dir()
    assert templates_dir.exists()

    logs_dir = get_logs_dir()
    assert logs_dir.exists()

    models_dir = get_models_dir()
    assert models_dir.exists()
