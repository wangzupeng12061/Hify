"""create job tables

Revision ID: jobs_20260622_0001
Revises: agents_20260622_0002
Create Date: 2026-06-22 00:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "jobs_20260622_0001"
down_revision: str | None = "agents_20260622_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("team_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("queue", sa.String(length=32), nullable=False),
        sa.Column("job_kind", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("attempt_count", sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_attempts", sa.BigInteger(), server_default=sa.text("3"), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("lease_owner", sa.Text(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
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
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_jobs_jobs__status",
        ),
        sa.CheckConstraint(
            "queue IN ('ingestion', 'embedding', 'llm_batch', 'events', 'maintenance')",
            name="ck_jobs_jobs__queue",
        ),
        sa.CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_jobs_jobs__idempotency_key_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(job_kind)) > 0",
            name="ck_jobs_jobs__job_kind_not_blank",
        ),
        sa.CheckConstraint("attempt_count >= 0", name="ck_jobs_jobs__attempt_count"),
        sa.CheckConstraint("max_attempts > 0", name="ck_jobs_jobs__max_attempts"),
        sa.CheckConstraint(
            "lease_owner IS NULL OR length(btrim(lease_owner)) > 0",
            name="ck_jobs_jobs__lease_owner_not_blank",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_jobs_jobs__team_idempotency_key",
        "jobs_jobs",
        ["team_id", "idempotency_key"],
        unique=True,
    )
    op.create_index(
        "pix_jobs_jobs__pending_queue_available",
        "jobs_jobs",
        ["queue", "available_at", "id"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "pix_jobs_jobs__running_lease_expired",
        "jobs_jobs",
        ["lease_expires_at", "id"],
        postgresql_where=sa.text("status = 'running'"),
    )
    op.create_index(
        "ix_jobs_jobs__team_status_created_id",
        "jobs_jobs",
        ["team_id", "status", "created_at", "id"],
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_jobs__team_status_created_id", table_name="jobs_jobs")
    op.drop_index("pix_jobs_jobs__running_lease_expired", table_name="jobs_jobs")
    op.drop_index("pix_jobs_jobs__pending_queue_available", table_name="jobs_jobs")
    op.drop_index("uq_jobs_jobs__team_idempotency_key", table_name="jobs_jobs")
    op.drop_table("jobs_jobs")
