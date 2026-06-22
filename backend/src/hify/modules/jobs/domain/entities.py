from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from hify.modules.jobs.domain.errors import JobStateConflictError
from hify.modules.jobs.domain.value_objects import (
    JobQueue,
    JobStatus,
    normalize_error_code,
    normalize_error_message,
    normalize_idempotency_key,
    normalize_job_kind,
    normalize_job_queue,
    normalize_lease_owner,
    normalize_payload,
    validate_max_attempts,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class Job:
    id: UUID
    team_id: UUID
    queue: JobQueue
    job_kind: str
    status: JobStatus
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

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        queue: str,
        job_kind: str,
        idempotency_key: str,
        payload: Mapping[str, object],
        max_attempts: int,
        available_at: datetime | None,
        created_by: UUID,
        now: datetime,
    ) -> Job:
        validate_max_attempts(max_attempts)
        return cls(
            id=new_uuid(),
            team_id=team_id,
            queue=normalize_job_queue(queue),
            job_kind=normalize_job_kind(job_kind),
            status=JobStatus.PENDING,
            idempotency_key=normalize_idempotency_key(idempotency_key),
            payload=normalize_payload(payload),
            attempt_count=0,
            max_attempts=max_attempts,
            available_at=available_at or now,
            lease_owner=None,
            lease_expires_at=None,
            created_by=created_by,
            created_at=now,
            updated_at=now,
            completed_at=None,
            error_code=None,
            error_message=None,
        )

    def claim(self, *, lease_owner: str, lease_expires_at: datetime, now: datetime) -> None:
        if self.status not in (JobStatus.PENDING, JobStatus.RUNNING):
            raise JobStateConflictError("job is not claimable")
        if self.status is JobStatus.PENDING and self.available_at > now:
            raise JobStateConflictError("job is not available yet")
        if self.status is JobStatus.RUNNING and (
            self.lease_expires_at is None or self.lease_expires_at > now
        ):
            raise JobStateConflictError("job lease has not expired")
        if self.attempt_count >= self.max_attempts:
            raise JobStateConflictError("job has no attempts remaining")

        self.status = JobStatus.RUNNING
        self.attempt_count += 1
        self.lease_owner = normalize_lease_owner(lease_owner)
        self.lease_expires_at = lease_expires_at
        self.error_code = None
        self.error_message = None
        self._mark_updated(now)

    def mark_succeeded(self, *, now: datetime) -> None:
        self._ensure_running()
        self.status = JobStatus.SUCCEEDED
        self.completed_at = now
        self.lease_owner = None
        self.lease_expires_at = None
        self.error_code = None
        self.error_message = None
        self._mark_updated(now)

    def mark_failed(
        self,
        *,
        error_code: str,
        error_message: str,
        retry_at: datetime | None,
        now: datetime,
    ) -> None:
        self._ensure_running()
        self.error_code = normalize_error_code(error_code)
        self.error_message = normalize_error_message(error_message)
        self.lease_owner = None
        self.lease_expires_at = None
        if retry_at is not None and self.attempt_count < self.max_attempts:
            self.status = JobStatus.PENDING
            self.available_at = retry_at
            self.completed_at = None
        else:
            self.status = JobStatus.FAILED
            self.completed_at = now
        self._mark_updated(now)

    def cancel(self, *, now: datetime) -> None:
        if self.status in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED):
            raise JobStateConflictError("job is already terminal")
        self.status = JobStatus.CANCELLED
        self.completed_at = now
        self.lease_owner = None
        self.lease_expires_at = None
        self._mark_updated(now)

    def _ensure_running(self) -> None:
        if self.status is not JobStatus.RUNNING:
            raise JobStateConflictError("job is not running")

    def _mark_updated(self, now: datetime) -> None:
        self.updated_at = now
