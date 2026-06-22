"""create agent tables

Revision ID: agents_20260622_0001
Revises: providers_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "agents_20260622_0001"
down_revision: str | None = "providers_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agents_agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("provider_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "latest_version_number",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="ck_agents_agents__status",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_agents_agents__name_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(system_prompt)) > 0",
            name="ck_agents_agents__system_prompt_not_blank",
        ),
        sa.CheckConstraint(
            "latest_version_number >= 0",
            name="ck_agents_agents__latest_version_number_non_negative",
        ),
    )
    op.create_index(
        "uq_agents_agents__team_name_lower",
        "agents_agents",
        ["team_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "ix_agents_agents__team_status_created_id",
        "agents_agents",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "agents_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version_number", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("provider_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("provider_name", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_display_name", sa.Text(), nullable=False),
        sa.Column("context_window_tokens", sa.BigInteger(), nullable=False),
        sa.Column("supports_tools", sa.Boolean(), nullable=False),
        sa.Column("supports_vision", sa.Boolean(), nullable=False),
        sa.Column("supports_structured_output", sa.Boolean(), nullable=False),
        sa.Column("published_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents_agents.id"]),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_agents_versions__version_number_positive",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_agents_versions__name_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(system_prompt)) > 0",
            name="ck_agents_versions__system_prompt_not_blank",
        ),
        sa.CheckConstraint(
            "context_window_tokens > 0",
            name="ck_agents_versions__context_window_tokens_positive",
        ),
    )
    op.create_index(
        "uq_agents_versions__agent_version_number",
        "agents_versions",
        ["agent_id", "version_number"],
        unique=True,
    )
    op.create_index(
        "ix_agents_versions__team_agent_version",
        "agents_versions",
        ["team_id", "agent_id", "version_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_agents_versions__team_agent_version", table_name="agents_versions")
    op.drop_index("uq_agents_versions__agent_version_number", table_name="agents_versions")
    op.drop_table("agents_versions")
    op.drop_index("ix_agents_agents__team_status_created_id", table_name="agents_agents")
    op.drop_index("uq_agents_agents__team_name_lower", table_name="agents_agents")
    op.drop_table("agents_agents")
