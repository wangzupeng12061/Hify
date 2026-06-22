"""create workflow tables

Revision ID: workflows_20260622_0001
Revises: tools_20260622_0002
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "workflows_20260622_0001"
down_revision: str | None = "tools_20260622_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workflows_workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "draft_definition",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("latest_version_number", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("version", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_workflows_workflows__status",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_workflows_workflows__name_not_blank",
        ),
        sa.CheckConstraint(
            "latest_version_number >= 0",
            name="ck_workflows_workflows__latest_version_number_non_negative",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_workflows_workflows__team_name_lower",
        "workflows_workflows",
        ["team_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "ix_workflows_workflows__team_status_created_id",
        "workflows_workflows",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "workflows_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("definition", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_workflows_versions__version_number_positive",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_workflows_versions__name_not_blank",
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows_workflows.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_workflows_versions__workflow_version_number",
        "workflows_versions",
        ["workflow_id", "version_number"],
        unique=True,
    )
    op.create_index(
        "ix_workflows_versions__team_workflow_version",
        "workflows_versions",
        ["team_id", "workflow_id", "version_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_workflows_versions__team_workflow_version", table_name="workflows_versions")
    op.drop_index("uq_workflows_versions__workflow_version_number", table_name="workflows_versions")
    op.drop_table("workflows_versions")
    op.drop_index("ix_workflows_workflows__team_status_created_id", table_name="workflows_workflows")
    op.drop_index("uq_workflows_workflows__team_name_lower", table_name="workflows_workflows")
    op.drop_table("workflows_workflows")
