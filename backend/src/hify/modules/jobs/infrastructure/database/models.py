from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.jobs.domain.value_objects import JobQueue, JobStatus
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class JobModel(Base):
    __tablename__ = "jobs_jobs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')",
            name="ck_jobs_jobs__status",
        ),
        CheckConstraint(
            "queue IN ('ingestion', 'embedding', 'llm_batch', 'events', 'maintenance')",
            name="ck_jobs_jobs__queue",
        ),
        CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_jobs_jobs__idempotency_key_not_blank",
        ),
        CheckConstraint(
            "length(btrim(job_kind)) > 0",
            name="ck_jobs_jobs__job_kind_not_blank",
        ),
        CheckConstraint("attempt_count >= 0", name="ck_jobs_jobs__attempt_count"),
        CheckConstraint("max_attempts > 0", name="ck_jobs_jobs__max_attempts"),
        CheckConstraint(
            "lease_owner IS NULL OR length(btrim(lease_owner)) > 0",
            name="ck_jobs_jobs__lease_owner_not_blank",
        ),
        Index(
            "uq_jobs_jobs__team_idempotency_key",
            "team_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "pix_jobs_jobs__pending_queue_available",
            "queue",
            "available_at",
            "id",
            postgresql_where=text("status = 'pending'"),
        ),
        Index(
            "pix_jobs_jobs__running_lease_expired",
            "lease_expires_at",
            "id",
            postgresql_where=text("status = 'running'"),
        ),
        Index(
            "ix_jobs_jobs__team_status_created_id",
            "team_id",
            "status",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    queue: Mapped[str] = mapped_column(String(32), nullable=False, default=JobQueue.MAINTENANCE.value)
    job_kind: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=JobStatus.PENDING.value)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    attempt_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    max_attempts: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=3,
        server_default=text("3"),
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    lease_owner: Mapped[str | None] = mapped_column(Text, nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
