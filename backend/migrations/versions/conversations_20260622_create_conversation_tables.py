"""create conversation tables

Revision ID: conversations_20260622_0001
Revises: agents_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "conversations_20260622_0001"
down_revision: str | None = "agents_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
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
            "status IN ('active', 'archived')",
            name="ck_conversations_conversations__status",
        ),
        sa.CheckConstraint(
            "title IS NULL OR length(btrim(title)) > 0",
            name="ck_conversations_conversations__title_not_blank",
        ),
        sa.CheckConstraint(
            "message_count >= 0",
            name="ck_conversations_conversations__message_count_non_negative",
        ),
    )
    op.create_index(
        "ix_conversations_conversations__team_status_created_id",
        "conversations_conversations",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_conversations_conversations__team_agent_created_id",
        "conversations_conversations",
        ["team_id", "agent_id", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "conversations_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations_conversations.id"]),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_conversations_messages__sequence_number_positive",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')",
            name="ck_conversations_messages__role",
        ),
        sa.CheckConstraint(
            "status IN ('created', 'redacted')",
            name="ck_conversations_messages__status",
        ),
        sa.CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_conversations_messages__content_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_conversations_messages__idempotency_key_not_blank",
        ),
    )
    op.create_index(
        "uq_conversations_messages__conversation_sequence",
        "conversations_messages",
        ["conversation_id", "sequence_number"],
        unique=True,
    )
    op.create_index(
        "uq_conversations_messages__team_conversation_idempotency",
        "conversations_messages",
        ["team_id", "conversation_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_conversations_messages__team_conversation_sequence",
        "conversations_messages",
        ["team_id", "conversation_id", "sequence_number"],
        unique=False,
    )

    op.create_table(
        "conversations_message_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations_conversations.id"]),
        sa.ForeignKeyConstraint(["message_id"], ["conversations_messages.id"]),
        sa.CheckConstraint(
            "rating IN ('positive', 'negative')",
            name="ck_conversations_message_feedback__rating",
        ),
    )
    op.create_index(
        "uq_conversations_message_feedback__message_created_by",
        "conversations_message_feedback",
        ["message_id", "created_by"],
        unique=True,
    )
    op.create_index(
        "ix_conversations_message_feedback__team_conversation_created",
        "conversations_message_feedback",
        ["team_id", "conversation_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversations_message_feedback__team_conversation_created",
        table_name="conversations_message_feedback",
    )
    op.drop_index(
        "uq_conversations_message_feedback__message_created_by",
        table_name="conversations_message_feedback",
    )
    op.drop_table("conversations_message_feedback")
    op.drop_index(
        "ix_conversations_messages__team_conversation_sequence",
        table_name="conversations_messages",
    )
    op.drop_index(
        "uq_conversations_messages__team_conversation_idempotency",
        table_name="conversations_messages",
    )
    op.drop_index(
        "uq_conversations_messages__conversation_sequence",
        table_name="conversations_messages",
    )
    op.drop_table("conversations_messages")
    op.drop_index(
        "ix_conversations_conversations__team_agent_created_id",
        table_name="conversations_conversations",
    )
    op.drop_index(
        "ix_conversations_conversations__team_status_created_id",
        table_name="conversations_conversations",
    )
    op.drop_table("conversations_conversations")
