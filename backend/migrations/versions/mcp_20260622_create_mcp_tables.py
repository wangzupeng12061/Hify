"""create mcp tables

Revision ID: mcp_20260622_0001
Revises: jobs_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "mcp_20260622_0001"
down_revision: str | None = "jobs_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "mcp_servers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("endpoint_url", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
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
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_mcp_servers__status"),
        sa.CheckConstraint("transport IN ('streamable_http')", name="ck_mcp_servers__transport"),
        sa.CheckConstraint("length(btrim(name)) > 0", name="ck_mcp_servers__name_not_blank"),
        sa.CheckConstraint(
            "endpoint_url LIKE 'https://%'",
            name="ck_mcp_servers__endpoint_https",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_mcp_servers__team_name_lower",
        "mcp_servers",
        ["team_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "ix_mcp_servers__team_status_created_id",
        "mcp_servers",
        ["team_id", "status", "created_at", "id"],
    )
    op.create_table(
        "mcp_discovered_tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("server_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
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
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_mcp_discovered_tools__status",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_mcp_discovered_tools__name_not_blank",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(input_schema) = 'object'",
            name="ck_mcp_discovered_tools__input_schema_object",
        ),
        sa.ForeignKeyConstraint(["server_id"], ["mcp_servers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_mcp_discovered_tools__server_name",
        "mcp_discovered_tools",
        ["server_id", "name"],
        unique=True,
    )
    op.create_index(
        "ix_mcp_discovered_tools__team_server_status_name",
        "mcp_discovered_tools",
        ["team_id", "server_id", "status", "name"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_mcp_discovered_tools__team_server_status_name",
        table_name="mcp_discovered_tools",
    )
    op.drop_index("uq_mcp_discovered_tools__server_name", table_name="mcp_discovered_tools")
    op.drop_table("mcp_discovered_tools")
    op.drop_index("ix_mcp_servers__team_status_created_id", table_name="mcp_servers")
    op.drop_index("uq_mcp_servers__team_name_lower", table_name="mcp_servers")
    op.drop_table("mcp_servers")
