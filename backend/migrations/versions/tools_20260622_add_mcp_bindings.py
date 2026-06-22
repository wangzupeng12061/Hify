"""add mcp bindings to tools

Revision ID: tools_20260622_0002
Revises: mcp_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "tools_20260622_0002"
down_revision: str | None = "mcp_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_tools_definitions__tool_kind", "tools_definitions", type_="check")
    op.add_column(
        "tools_definitions",
        sa.Column("mcp_server_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "tools_definitions",
        sa.Column("mcp_tool_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column("tools_definitions", sa.Column("mcp_tool_name", sa.Text(), nullable=True))
    op.create_check_constraint(
        "ck_tools_definitions__tool_kind",
        "tools_definitions",
        "tool_kind IN ('builtin', 'http', 'mcp')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tools_definitions__tool_kind", "tools_definitions", type_="check")
    op.drop_column("tools_definitions", "mcp_tool_name")
    op.drop_column("tools_definitions", "mcp_tool_id")
    op.drop_column("tools_definitions", "mcp_server_id")
    op.create_check_constraint(
        "ck_tools_definitions__tool_kind",
        "tools_definitions",
        "tool_kind IN ('builtin', 'http')",
    )
