"""Per-user storage key builders. Everything is namespaced under ``users/{uid}/``."""

from __future__ import annotations


def user_prefix(user_id: str) -> str:
    return f"users/{user_id}"


def resume_key(user_id: str, resume_id: str, ext: str) -> str:
    return f"{user_prefix(user_id)}/resumes/{resume_id}.{ext}"


def upload_key(user_id: str, upload_id: str, ext: str) -> str:
    return f"{user_prefix(user_id)}/uploads/{upload_id}.{ext}"


def cover_letter_key(user_id: str, application_id: str, ext: str) -> str:
    return f"{user_prefix(user_id)}/cover_letters/{application_id}.{ext}"


def screenshot_key(user_id: str, application_id: str, name: str) -> str:
    return f"{user_prefix(user_id)}/screenshots/{application_id}/{name}"


def trajectory_key(user_id: str, run_id: str) -> str:
    return f"{user_prefix(user_id)}/trajectories/{run_id}.json"
