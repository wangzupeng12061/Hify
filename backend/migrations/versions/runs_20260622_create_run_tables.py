"""create run tables

Revision ID: runs_20260622_0001
Revises: conversations_20260622_0001
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "runs_20260622_0001"
down_revision: str | None = "conversations_20260622_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "runs_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("step_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("event_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
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
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'interrupted')",
            name="ck_runs_runs__status",
        ),
        sa.CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_runs_runs__idempotency_key_not_blank",
        ),
        sa.CheckConstraint("step_count >= 0", name="ck_runs_runs__step_count_non_negative"),
        sa.CheckConstraint("event_count >= 0", name="ck_runs_runs__event_count_non_negative"),
    )
    op.create_index(
        "uq_runs_runs__team_conversation_idempotency",
        "runs_runs",
        ["team_id", "conversation_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "ix_runs_runs__team_status_created_id",
        "runs_runs",
        ["team_id", "status", "created_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_runs_runs__team_conversation_created_id",
        "runs_runs",
        ["team_id", "conversation_id", "created_at", "id"],
        unique=False,
    )

    op.create_table(
        "runs_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.BigInteger(), nullable=False),
        sa.Column("step_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["run_id"], ["runs_runs.id"]),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_runs_steps__sequence_number_positive",
        ),
        sa.CheckConstraint(
            "step_type IN ('llm_call', 'tool_call', 'retrieval', 'system')",
            name="ck_runs_steps__step_type",
        ),
        sa.CheckConstraint(
            "status IN ('started', 'succeeded', 'failed', 'cancelled')",
            name="ck_runs_steps__status",
        ),
    )
    op.create_index(
        "uq_runs_steps__run_sequence",
        "runs_steps",
        ["run_id", "sequence_number"],
        unique=True,
    )
    op.create_index(
        "ix_runs_steps__team_run_sequence",
        "runs_steps",
        ["team_id", "run_id", "sequence_number"],
        unique=False,
    )

    op.create_table(
        "runs_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sequence_number", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["run_id"], ["runs_runs.id"]),
        sa.CheckConstraint(
            "sequence_number > 0",
            name="ck_runs_events__sequence_number_positive",
        ),
        sa.CheckConstraint(
            "event_type IN ("
            "'run.created', 'run.started', 'run.succeeded', 'run.failed', "
            "'run.cancelled', 'run.interrupted', 'step.started', 'step.succeeded', "
            "'step.failed', 'output.text_delta', 'diagnostic'"
            ")",
            name="ck_runs_events__event_type",
        ),
    )
    op.create_index(
        "uq_runs_events__run_sequence",
        "runs_events",
        ["run_id", "sequence_number"],
        unique=True,
    )
    op.create_index(
        "ix_runs_events__team_run_sequence",
        "runs_events",
        ["team_id", "run_id", "sequence_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_runs_events__team_run_sequence", table_name="runs_events")
    op.drop_index("uq_runs_events__run_sequence", table_name="runs_events")
    op.drop_table("runs_events")
    op.drop_index("ix_runs_steps__team_run_sequence", table_name="runs_steps")
    op.drop_index("uq_runs_steps__run_sequence", table_name="runs_steps")
    op.drop_table("runs_steps")
    op.drop_index("ix_runs_runs__team_conversation_created_id", table_name="runs_runs")
    op.drop_index("ix_runs_runs__team_status_created_id", table_name="runs_runs")
    op.drop_index("uq_runs_runs__team_conversation_idempotency", table_name="runs_runs")
    op.drop_table("runs_runs")
