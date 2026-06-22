"""create tool tables

Revision ID: tools_20260622_0001
Revises: runs_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "tools_20260622_0001"
down_revision: str | None = "runs_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tools_definitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tool_kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column(
            "input_schema",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("builtin_name", sa.Text(), nullable=True),
        sa.Column("endpoint_url", sa.Text(), nullable=True),
        sa.Column("http_method", sa.String(length=32), nullable=True),
        sa.Column(
            "http_headers",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
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
            "tool_kind IN ('builtin', 'http')",
            name="ck_tools_definitions__tool_kind",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_tools_definitions__status",
        ),
        sa.CheckConstraint(
            "http_method IS NULL OR http_method IN ('GET', 'POST', 'PUT', 'PATCH', 'DELETE')",
            name="ck_tools_definitions__http_method",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_tools_definitions__name_not_blank",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(input_schema) = 'object'",
            name="ck_tools_definitions__input_schema_object",
        ),
    )
    op.create_index(
        "uq_tools_definitions__team_name_lower",
        "tools_definitions",
        ["team_id", sa.text("lower(name)")],
        unique=True,
    )
    op.create_index(
        "ix_tools_definitions__team_status_created_id",
        "tools_definitions",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tools_definitions__team_status_created_id", table_name="tools_definitions")
    op.drop_index("uq_tools_definitions__team_name_lower", table_name="tools_definitions")
    op.drop_table("tools_definitions")
