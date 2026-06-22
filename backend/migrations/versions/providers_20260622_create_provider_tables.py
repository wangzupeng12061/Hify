"""create provider tables

Revision ID: providers_20260622_0001
Revises: identity_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "providers_20260622_0001"
down_revision: str | None = "identity_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "providers_providers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
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
            "provider_type IN ('openai', 'anthropic', 'gemini', 'ollama')",
            name="ck_providers_providers__provider_type",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_providers_providers__status",
        ),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_providers_providers__name_not_blank",
        ),
    )
    op.create_index(
        "uq_providers_providers__team_type_name_lower",
        "providers_providers",
        ["team_id", "provider_type", sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "providers_credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("secret_ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("key_version", sa.BigInteger(), nullable=False),
        sa.Column("secret_fingerprint", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
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
        sa.ForeignKeyConstraint(["provider_id"], ["providers_providers.id"]),
        sa.UniqueConstraint("provider_id", name="uq_providers_credentials__provider_id"),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_providers_credentials__status",
        ),
        sa.CheckConstraint(
            "key_version > 0",
            name="ck_providers_credentials__key_version_positive",
        ),
    )

    op.create_table(
        "providers_models",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("context_window_tokens", sa.BigInteger(), nullable=False),
        sa.Column("supports_tools", sa.Boolean(), nullable=False),
        sa.Column("supports_vision", sa.Boolean(), nullable=False),
        sa.Column("supports_structured_output", sa.Boolean(), nullable=False),
        sa.Column("version", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
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
        sa.ForeignKeyConstraint(["provider_id"], ["providers_providers.id"]),
        sa.CheckConstraint("kind IN ('chat', 'embedding')", name="ck_providers_models__kind"),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_providers_models__status",
        ),
        sa.CheckConstraint(
            "length(btrim(model_name)) > 0",
            name="ck_providers_models__model_name_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_providers_models__display_name_not_blank",
        ),
        sa.CheckConstraint(
            "context_window_tokens > 0",
            name="ck_providers_models__context_window_tokens_positive",
        ),
    )
    op.create_index(
        "uq_providers_models__provider_model_name_lower",
        "providers_models",
        ["provider_id", sa.text("lower(model_name)")],
        unique=True,
    )
    op.create_index(
        "ix_providers_models__team_status_created_id",
        "providers_models",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_providers_models__team_status_created_id", table_name="providers_models")
    op.drop_index("uq_providers_models__provider_model_name_lower", table_name="providers_models")
    op.drop_table("providers_models")
    op.drop_table("providers_credentials")
    op.drop_index("uq_providers_providers__team_type_name_lower", table_name="providers_providers")
    op.drop_table("providers_providers")
