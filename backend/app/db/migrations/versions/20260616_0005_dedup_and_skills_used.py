"""dedup active applications + run_trajectory.skills_used

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-16 10:00:00.000000+00:00

Adds:
- A partial-unique index ``uq_app_active_job`` so a (user_id, job_id) can have at most one
  ACTIVE application (terminal rejected/withdrawn/failed are excluded → re-apply allowed).
- ``run_trajectories.skills_used`` (JSON): the domain-skill ids injected into a run, so the
  harness verdict can feed back to score them.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_ACTIVE = "status NOT IN ('rejected', 'withdrawn', 'failed')"


def upgrade() -> None:
    with op.batch_alter_table("run_trajectories") as batch_op:
        batch_op.add_column(sa.Column("skills_used", sa.JSON(), nullable=True))
    op.create_index(
        "uq_app_active_job",
        "applications",
        ["user_id", "job_id"],
        unique=True,
        sqlite_where=sa.text(_ACTIVE),
        postgresql_where=sa.text(_ACTIVE),
    )


def downgrade() -> None:
    op.drop_index("uq_app_active_job", table_name="applications")
    with op.batch_alter_table("run_trajectories") as batch_op:
        batch_op.drop_column("skills_used")
