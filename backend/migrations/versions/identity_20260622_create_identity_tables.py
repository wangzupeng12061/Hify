"""create identity tables

Revision ID: identity_20260622_0001
Revises: shared_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "identity_20260622_0001"
down_revision: str | None = "shared_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "identity_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
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
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_identity_users__status"),
        sa.CheckConstraint(
            "length(btrim(email)) > 0",
            name="ck_identity_users__email_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(display_name)) > 0",
            name="ck_identity_users__display_name_not_blank",
        ),
    )
    op.create_index(
        "uq_identity_users__email_lower",
        "identity_users",
        [sa.text("lower(email)")],
        unique=True,
    )

    op.create_table(
        "identity_teams",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
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
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_identity_teams__status"),
        sa.CheckConstraint(
            "length(btrim(name)) > 0",
            name="ck_identity_teams__name_not_blank",
        ),
    )
    op.create_index(
        "uq_identity_teams__name_lower",
        "identity_teams",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.create_table(
        "identity_memberships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
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
        sa.ForeignKeyConstraint(["team_id"], ["identity_teams.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["identity_users.id"]),
        sa.UniqueConstraint("team_id", "user_id", name="uq_identity_memberships__team_user"),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="ck_identity_memberships__role",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')",
            name="ck_identity_memberships__status",
        ),
    )
    op.create_index(
        "ix_identity_memberships__team_status_created_id",
        "identity_memberships",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_identity_memberships__user_status_created_id",
        "identity_memberships",
        ["user_id", "status", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_identity_memberships__user_status_created_id", table_name="identity_memberships")
    op.drop_index("ix_identity_memberships__team_status_created_id", table_name="identity_memberships")
    op.drop_table("identity_memberships")
    op.drop_index("uq_identity_teams__name_lower", table_name="identity_teams")
    op.drop_table("identity_teams")
    op.drop_index("uq_identity_users__email_lower", table_name="identity_users")
    op.drop_table("identity_users")
