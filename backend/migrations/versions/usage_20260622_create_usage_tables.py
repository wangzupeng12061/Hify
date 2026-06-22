"""create usage tables

Revision ID: usage_20260622_0001
Revises: agents_20260622_0003
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "usage_20260622_0001"
down_revision: str | None = "agents_20260622_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usage_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_model_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), nullable=False),
        sa.Column("output_tokens", sa.BigInteger(), nullable=False),
        sa.Column("total_tokens", sa.BigInteger(), nullable=False),
        sa.Column("cost_amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(btrim(provider)) > 0",
            name="ck_usage_records__provider_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(model)) > 0",
            name="ck_usage_records__model_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_usage_records__idempotency_key_not_blank",
        ),
        sa.CheckConstraint("input_tokens >= 0", name="ck_usage_records__input_tokens"),
        sa.CheckConstraint("output_tokens >= 0", name="ck_usage_records__output_tokens"),
        sa.CheckConstraint("total_tokens >= 0", name="ck_usage_records__total_tokens"),
        sa.CheckConstraint("cost_amount >= 0", name="ck_usage_records__cost_amount"),
    )
    op.create_index(
        "uq_usage_records__team_idempotency_key",
        "usage_records",
        ["team_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_usage_records__team_occurred_id",
        "usage_records",
        ["team_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_usage_records__team_run_occurred_id",
        "usage_records",
        ["team_id", "run_id", "occurred_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_records__team_run_occurred_id", table_name="usage_records")
    op.drop_index("ix_usage_records__team_occurred_id", table_name="usage_records")
    op.drop_index("uq_usage_records__team_idempotency_key", table_name="usage_records")
    op.drop_table("usage_records")
