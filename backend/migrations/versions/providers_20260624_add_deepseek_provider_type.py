"""add deepseek provider type

Revision ID: providers_20260624_0003
Revises: identity_20260624_0002
Create Date: 2026-06-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "providers_20260624_0003"
down_revision: str | None = "identity_20260624_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_providers_providers__provider_type",
        "providers_providers",
        type_="check",
    )
    op.create_check_constraint(
        "ck_providers_providers__provider_type",
        "providers_providers",
        "provider_type IN ('openai', 'anthropic', 'gemini', 'ollama', 'deepseek')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_providers_providers__provider_type",
        "providers_providers",
        type_="check",
    )
    op.create_check_constraint(
        "ck_providers_providers__provider_type",
        "providers_providers",
        "provider_type IN ('openai', 'anthropic', 'gemini', 'ollama')",
    )
