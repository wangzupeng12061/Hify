"""create usage quota tables

Revision ID: usage_20260623_0002
Revises: usage_20260622_0001
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "usage_20260623_0002"
down_revision: str | None = "usage_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_quotas",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("monthly_token_limit", sa.BigInteger(), nullable=True),
        sa.Column("version", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
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
            "monthly_token_limit IS NULL OR monthly_token_limit > 0",
            name="ck_usage_quotas__monthly_token_limit",
        ),
    )
    op.create_index(
        "uq_usage_quotas__team",
        "usage_quotas",
        ["team_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_usage_quotas__team", table_name="usage_quotas")
    op.drop_table("usage_quotas")
