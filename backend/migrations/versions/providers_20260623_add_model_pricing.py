"""add provider model pricing

Revision ID: providers_20260623_0002
Revises: usage_20260623_0002
Create Date: 2026-06-23 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "providers_20260623_0002"
down_revision: str | None = "usage_20260623_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "providers_models",
        sa.Column("price_per_1m_input_tokens", sa.Numeric(20, 8), nullable=True),
    )
    op.add_column(
        "providers_models",
        sa.Column("price_per_1m_output_tokens", sa.Numeric(20, 8), nullable=True),
    )
    op.create_check_constraint(
        "ck_providers_models__input_price_non_negative",
        "providers_models",
        "price_per_1m_input_tokens IS NULL OR price_per_1m_input_tokens >= 0",
    )
    op.create_check_constraint(
        "ck_providers_models__output_price_non_negative",
        "providers_models",
        "price_per_1m_output_tokens IS NULL OR price_per_1m_output_tokens >= 0",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_providers_models__output_price_non_negative",
        "providers_models",
        type_="check",
    )
    op.drop_constraint(
        "ck_providers_models__input_price_non_negative",
        "providers_models",
        type_="check",
    )
    op.drop_column("providers_models", "price_per_1m_output_tokens")
    op.drop_column("providers_models", "price_per_1m_input_tokens")
