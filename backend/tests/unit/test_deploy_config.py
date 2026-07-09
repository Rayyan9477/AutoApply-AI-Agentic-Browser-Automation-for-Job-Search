"""Deploy-config regression guards (review findings H1 + H2).

These can't be exercised by running the app in-process, so they assert on the files directly:
  * every RESUME_TEMPLATES entry has an on-disk template (H1: templates must ship in the image);
  * both Dockerfiles COPY the repo-root templates/ dir (H1);
  * the API Dockerfile launches uvicorn with --proxy-headers (H2: real client IP behind Caddy).
"""

from pathlib import Path

import pytest

from app.config.constants import RESUME_TEMPLATES

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATES = _REPO_ROOT / "templates"
_DOCKERFILE_API = _REPO_ROOT / "docker" / "Dockerfile.api"
_DOCKERFILE_WORKER = _REPO_ROOT / "docker" / "Dockerfile.worker"


@pytest.mark.parametrize("name", RESUME_TEMPLATES)
def test_resume_template_exists_on_disk(name: str) -> None:
    tpl = _TEMPLATES / "resume" / name / "template.html"
    assert tpl.is_file(), f"missing resume template for '{name}': {tpl}"


def test_cover_letter_templates_exist() -> None:
    # select_best_template can return any of these; each needs a template dir.
    for name in ("standard", "technical", "creative"):
        tpl = _TEMPLATES / "cover_letter" / name / "template.html"
        assert tpl.is_file(), f"missing cover-letter template: {tpl}"


def test_dockerfiles_copy_templates() -> None:
    for df in (_DOCKERFILE_API, _DOCKERFILE_WORKER):
        text = df.read_text(encoding="utf-8")
        assert "COPY templates/" in text, f"{df.name} does not COPY templates/ into the image"


def test_api_dockerfile_trusts_proxy_headers() -> None:
    text = _DOCKERFILE_API.read_text(encoding="utf-8")
    assert "--proxy-headers" in text, "API image must run uvicorn with --proxy-headers behind Caddy"
