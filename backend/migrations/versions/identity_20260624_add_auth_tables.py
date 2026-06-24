"""add identity auth tables

Revision ID: identity_20260624_0002
Revises: runs_20260623_0002
Create Date: 2026-06-24 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "identity_20260624_0002"
down_revision: str | None = "runs_20260623_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_token_hash", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["identity_teams.id"]),
        sa.CheckConstraint(
            "length(btrim(session_token_hash)) > 0",
            name="ck_identity_sessions__token_hash_not_blank",
        ),
        sa.CheckConstraint(
            "expires_at > created_at",
            name="ck_identity_sessions__expires_after_created",
        ),
    )
    op.create_index(
        "uq_identity_sessions__token_hash",
        "identity_sessions",
        ["session_token_hash"],
        unique=True,
    )
    op.create_index(
        "ix_identity_sessions__expires_at_id",
        "identity_sessions",
        ["expires_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_identity_sessions__user_expires_id",
        "identity_sessions",
        ["user_id", "expires_at", "id"],
        unique=False,
    )

    op.create_table(
        "identity_external_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"]),
        sa.UniqueConstraint(
            "provider",
            "subject",
            name="uq_identity_external_accounts__provider_subject",
        ),
        sa.CheckConstraint(
            "length(btrim(provider)) > 0",
            name="ck_identity_external_accounts__provider_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(subject)) > 0",
            name="ck_identity_external_accounts__subject_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(email)) > 0",
            name="ck_identity_external_accounts__email_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_identity_external_accounts__display_name_not_blank",
        ),
    )
    op.create_index(
        "ix_identity_external_accounts__user_provider_id",
        "identity_external_accounts",
        ["user_id", "provider", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_identity_external_accounts__user_provider_id",
        table_name="identity_external_accounts",
    )
    op.drop_table("identity_external_accounts")
    op.drop_index("ix_identity_sessions__user_expires_id", table_name="identity_sessions")
    op.drop_index("ix_identity_sessions__expires_at_id", table_name="identity_sessions")
    op.drop_index("uq_identity_sessions__token_hash", table_name="identity_sessions")
    op.drop_table("identity_sessions")
