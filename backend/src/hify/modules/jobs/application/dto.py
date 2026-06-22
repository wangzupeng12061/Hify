from __future__ import annotations

from hify.modules.jobs.contracts.dto import JobInfo
from hify.modules.jobs.domain.entities import Job


def job_info_from_domain(job: Job) -> JobInfo:
    return JobInfo(
        id=job.id,
        team_id=job.team_id,
        queue=job.queue.value,
        job_kind=job.job_kind,
        status=job.status.value,
        idempotency_key=job.idempotency_key,
        payload=dict(job.payload),
        attempt_count=job.attempt_count,
        max_attempts=job.max_attempts,
        available_at=job.available_at,
        lease_owner=job.lease_owner,
        lease_expires_at=job.lease_expires_at,
        created_by=job.created_by,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        error_code=job.error_code,
        error_message=job.error_message,
    )
