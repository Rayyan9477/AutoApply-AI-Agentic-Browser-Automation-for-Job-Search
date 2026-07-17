"""add 'general' to llm_purpose enum

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-13 13:10:00.000000+00:00

Adds a catch-all ``general`` value to the ``llm_purpose`` enum (the LLMClient's default
"general"/"structured" labels coerce here when persisting usage rows).

PostgreSQL enforces the enum as a native type, so the value must be added with
``ALTER TYPE``. SQLite stores ``pg_enum`` columns as unconstrained ``VARCHAR`` (membership
is validated Python-side via ``validate_strings``), so no schema change is needed there.
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        # PG 12+ permits ADD VALUE inside a transaction; idempotent on partial state.
        op.execute("ALTER TYPE llm_purpose ADD VALUE IF NOT EXISTS 'general'")


def downgrade() -> None:
    # Removing a value from a PostgreSQL enum that may be in use is unsupported; no-op.
    pass
