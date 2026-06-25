from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from hify.modules.runs.domain.value_objects import (
    RunEventType,
    RunStatus,
    RunStepStatus,
    RunStepType,
)
from hify.shared.domain.clock import utc_now
from hify.shared.domain.ids import new_uuid
from hify.shared.infrastructure.database import Base


class RunModel(Base):
    __tablename__ = "runs_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled', 'interrupted')",
            name="ck_runs_runs__status",
        ),
        CheckConstraint(
            "length(btrim(idempotency_key)) > 0",
            name="ck_runs_runs__idempotency_key_not_blank",
        ),
        CheckConstraint("step_count >= 0", name="ck_runs_runs__step_count_non_negative"),
        CheckConstraint("event_count >= 0", name="ck_runs_runs__event_count_non_negative"),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_runs_runs__duration_ms_non_negative",
        ),
        Index(
            "uq_runs_runs__team_conversation_idempotency",
            "team_id",
            "conversation_id",
            "idempotency_key",
            unique=True,
        ),
        Index(
            "ix_runs_runs__team_status_created_id",
            "team_id",
            "status",
            "created_at",
            "id",
        ),
        Index(
            "ix_runs_runs__team_conversation_created_id",
            "team_id",
            "conversation_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    conversation_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    agent_version_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=RunStatus.QUEUED.value)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    step_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    event_count: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
    version: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        default=0,
        server_default=text("0"),
    )
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
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RunStepModel(Base):
    __tablename__ = "runs_steps"
    __table_args__ = (
        CheckConstraint(
            "sequence_number > 0",
            name="ck_runs_steps__sequence_number_positive",
        ),
        CheckConstraint(
            "step_type IN ('llm_call', 'tool_call', 'retrieval', 'system')",
            name="ck_runs_steps__step_type",
        ),
        CheckConstraint(
            "status IN ('started', 'succeeded', 'failed', 'cancelled')",
            name="ck_runs_steps__status",
        ),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_runs_steps__duration_ms_non_negative",
        ),
        Index("uq_runs_steps__run_sequence", "run_id", "sequence_number", unique=True),
        Index("ix_runs_steps__team_run_sequence", "team_id", "run_id", "sequence_number"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("runs_runs.id"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    step_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RunStepType.SYSTEM.value,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=RunStepStatus.STARTED.value,
    )
    name: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class RunEventModel(Base):
    __tablename__ = "runs_events"
    __table_args__ = (
        CheckConstraint(
            "sequence_number > 0",
            name="ck_runs_events__sequence_number_positive",
        ),
        CheckConstraint(
            "event_type IN ("
            "'run.created', 'run.started', 'run.succeeded', 'run.failed', "
            "'run.cancelled', 'run.interrupted', 'step.started', 'step.succeeded', "
            "'step.failed', 'output.text_delta', 'diagnostic'"
            ")",
            name="ck_runs_events__event_type",
        ),
        Index("uq_runs_events__run_sequence", "run_id", "sequence_number", unique=True),
        Index("ix_runs_events__team_run_sequence", "team_id", "run_id", "sequence_number"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=new_uuid)
    team_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    run_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("runs_runs.id"),
        nullable=False,
    )
    sequence_number: Mapped[int] = mapped_column(BigInteger, nullable=False)
    event_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=RunEventType.DIAGNOSTIC.value,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=text("CURRENT_TIMESTAMP"),
    )
