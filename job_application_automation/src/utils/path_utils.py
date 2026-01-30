"""
Path utilities for job application automation.
"""

import os
from pathlib import Path
from typing import Union, Optional


def get_project_root() -> Path:
    """
    Get the project root directory.
    
    Returns:
        Path to the project root directory.
    """
    return Path(__file__).parent.parent.parent


def ensure_dir(directory: Union[str, Path]) -> Path:
    """
    Ensure a directory exists.
    
    Args:
        directory: Directory path to ensure exists.
        
    Returns:
        Path object for the directory.
    """
    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_data_path(subpath: Optional[str] = None) -> Path:
    """
    Get the path to the data directory or a subdirectory.
    
    Args:
        subpath: Optional subdirectory within the data directory.
        
    Returns:
        Path to the data directory or subdirectory.
    """
    data_dir = get_project_root() / "data"
    ensure_dir(data_dir)
    
    if subpath:
        subdir = data_dir / subpath
        ensure_dir(subdir)
        return subdir
    
    return data_dir


def get_templates_dir() -> Path:
    """
    Get the path to the templates directory.

    Returns:
        Path to the templates directory.
    """
    templates_dir = get_project_root() / "templates"
    ensure_dir(templates_dir)
    return templates_dir


def get_logs_dir() -> Path:
    """
    Get the path to the logs directory.

    Returns:
        Path to the logs directory.
    """
    logs_dir = get_data_path("logs")
    return logs_dir


def get_models_dir() -> Path:
    """
    Get the path to the models directory.

    Returns:
        Path to the models directory.
    """
    models_dir = get_project_root() / "models"
    ensure_dir(models_dir)
    return models_dir


def get_absolute_path(relative_path: str) -> Path:
    """
    Convert a relative path to an absolute path from the project root.
    
    Args:
        relative_path: Relative path from the project root.
        
    Returns:
        Absolute path.
    """
    if relative_path.startswith("../"):
        # Remove leading ../ and resolve from project root
        clean_path = relative_path.replace("../", "", 1)
        return get_project_root() / clean_path
    
    return Path(relative_path)
