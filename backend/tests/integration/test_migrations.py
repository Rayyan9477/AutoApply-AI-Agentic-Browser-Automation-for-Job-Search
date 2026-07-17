"""F5: the Alembic baseline applies cleanly from a clean DB.

SQLite always runs; Postgres runs only when ``TEST_POSTGRES_URL`` is set (CI).
"""

import os
import sqlite3

import pytest
from alembic import command
from alembic.config import Config

from app.config.settings import get_settings

EXPECTED_TABLES = {
    "users",
    "applications",
    "jobs",
    "resumes",
    "llm_usage",
    "refresh_tokens",
    "password_reset_tokens",
    "user_credentials",
    "user_llm_configs",
    "user_settings",
    "alembic_version",
}


def _run_upgrade_with_url(url: str) -> None:
    """Point the Alembic env (which reads get_settings) at ``url`` and upgrade to head."""
    old = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    get_settings.cache_clear()
    try:
        command.upgrade(Config("alembic.ini"), "head")
    finally:
        if old is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old
        get_settings.cache_clear()


def test_sqlite_upgrade_head_from_clean(tmp_path):
    db = tmp_path / "migration_test.db"
    _run_upgrade_with_url(f"sqlite+aiosqlite:///{db.as_posix()}")

    con = sqlite3.connect(str(db))
    try:
        tables = {r[0] for r in con.execute("select name from sqlite_master where type='table'")}
    finally:
        con.close()
    assert tables >= EXPECTED_TABLES, f"missing: {EXPECTED_TABLES - tables}"


@pytest.mark.skipif(
    not os.environ.get("TEST_POSTGRES_URL"),
    reason="set TEST_POSTGRES_URL to verify the migration on PostgreSQL",
)
def test_postgres_upgrade_head_from_clean():
    _run_upgrade_with_url(os.environ["TEST_POSTGRES_URL"])
