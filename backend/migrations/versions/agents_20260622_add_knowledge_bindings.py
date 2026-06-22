"""add agent knowledge bindings

Revision ID: agents_20260622_0002
Revises: knowledge_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "agents_20260622_0002"
down_revision: str | None = "knowledge_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agents_agents",
        sa.Column(
            "knowledge_base_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )
    op.add_column(
        "agents_versions",
        sa.Column(
            "knowledge_base_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
    )


def downgrade() -> None:
    op.drop_column("agents_versions", "knowledge_base_ids")
    op.drop_column("agents_agents", "knowledge_base_ids")
