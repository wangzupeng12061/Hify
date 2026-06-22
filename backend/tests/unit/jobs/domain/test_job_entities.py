from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from hify.modules.jobs.domain.entities import Job
from hify.modules.jobs.domain.errors import JobStateConflictError, JobValidationError
from hify.modules.jobs.domain.value_objects import JobStatus


NOW = datetime(2026, 6, 22, tzinfo=UTC)
TEAM_ID = UUID("00000000-0000-7000-8000-000000000001")
USER_ID = UUID("00000000-0000-7000-8000-000000000002")


def test_job_lifecycle_claim_retry_and_succeed() -> None:
    job = Job.create(
        team_id=TEAM_ID,
        queue="ingestion",
        job_kind="knowledge.document_ingestion",
        idempotency_key="document-1",
        payload={"document_id": "00000000-0000-7000-8000-000000000003"},
        max_attempts=3,
        available_at=None,
        created_by=USER_ID,
        now=NOW,
    )

    job.claim(
        lease_owner="worker-1",
        lease_expires_at=NOW + timedelta(minutes=5),
        now=NOW,
    )
    assert job.status is JobStatus.RUNNING
    assert job.attempt_count == 1

    retry_at = NOW + timedelta(minutes=1)
    job.mark_failed(
        error_code="temporary_failure",
        error_message="provider timed out",
        retry_at=retry_at,
        now=NOW,
    )
    assert job.status is JobStatus.PENDING
    assert job.available_at == retry_at
    assert job.lease_owner is None

    job.claim(
        lease_owner="worker-2",
        lease_expires_at=NOW + timedelta(minutes=10),
        now=retry_at,
    )
    job.mark_succeeded(now=NOW + timedelta(minutes=2))

    assert job.status is JobStatus.SUCCEEDED
    assert job.completed_at == NOW + timedelta(minutes=2)
    assert job.error_code is None


def test_job_claim_rejects_unavailable_pending_job() -> None:
    job = Job.create(
        team_id=TEAM_ID,
        queue="maintenance",
        job_kind="cleanup",
        idempotency_key="cleanup-1",
        payload={},
        max_attempts=1,
        available_at=NOW + timedelta(minutes=1),
        created_by=USER_ID,
        now=NOW,
    )

    with pytest.raises(JobStateConflictError):
        job.claim(
            lease_owner="worker-1",
            lease_expires_at=NOW + timedelta(minutes=5),
            now=NOW,
        )


def test_job_create_rejects_unsupported_queue() -> None:
    with pytest.raises(JobValidationError):
        Job.create(
            team_id=TEAM_ID,
            queue="unknown",
            job_kind="cleanup",
            idempotency_key="cleanup-1",
            payload={},
            max_attempts=1,
            available_at=None,
            created_by=USER_ID,
            now=NOW,
        )
