"""add run diagnostics duration fields

Revision ID: runs_20260623_0002
Revises: providers_20260623_0002
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "runs_20260623_0002"
down_revision: str | None = "providers_20260623_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "runs_runs",
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "runs_steps",
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_runs_runs__duration_ms_non_negative",
        "runs_runs",
        "duration_ms IS NULL OR duration_ms >= 0",
    )
    op.create_check_constraint(
        "ck_runs_steps__duration_ms_non_negative",
        "runs_steps",
        "duration_ms IS NULL OR duration_ms >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_runs_steps__duration_ms_non_negative",
        "runs_steps",
        type_="check",
    )
    op.drop_constraint(
        "ck_runs_runs__duration_ms_non_negative",
        "runs_runs",
        type_="check",
    )
    op.drop_column("runs_steps", "duration_ms")
    op.drop_column("runs_runs", "duration_ms")
