"""add workflow binding to agents

Revision ID: agents_20260622_0003
Revises: workflows_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "agents_20260622_0003"
down_revision: str | None = "workflows_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agents_agents",
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "agents_versions",
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "agents_versions",
        sa.Column("workflow_version_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "agents_versions",
        sa.Column("workflow_version_number", sa.BigInteger(), nullable=True),
    )
    op.add_column("agents_versions", sa.Column("workflow_name", sa.Text(), nullable=True))
    op.add_column(
        "agents_versions",
        sa.Column("workflow_definition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agents_versions", "workflow_definition")
    op.drop_column("agents_versions", "workflow_name")
    op.drop_column("agents_versions", "workflow_version_number")
    op.drop_column("agents_versions", "workflow_version_id")
    op.drop_column("agents_versions", "workflow_id")
    op.drop_column("agents_agents", "workflow_id")
