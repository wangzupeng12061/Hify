from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID


JOB_QUEUE_NAMES = ("ingestion", "embedding", "llm_batch", "events", "maintenance")


@dataclass(frozen=True, slots=True)
class ScheduleJobRequest:
    team_id: UUID
    queue: str
    job_kind: str
    idempotency_key: str
    payload: Mapping[str, object]
    created_by: UUID
    available_at: datetime | None = None
    max_attempts: int = 3


@dataclass(frozen=True, slots=True)
class JobInfo:
    id: UUID
    team_id: UUID
    queue: str
    job_kind: str
    status: str
    idempotency_key: str
    payload: Mapping[str, object]
    attempt_count: int
    max_attempts: int
    available_at: datetime
    lease_owner: str | None
    lease_expires_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None
    error_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class ClaimedJob:
    job: JobInfo
    lease_owner: str
    lease_expires_at: datetime
