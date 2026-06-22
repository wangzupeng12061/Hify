from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.jobs.domain.entities import Job
from hify.modules.jobs.domain.value_objects import JobQueue, JobStatus, normalize_job_queue
from hify.modules.jobs.infrastructure.database.models import JobModel


class SqlAlchemyJobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, job: Job) -> None:
        self._session.add(_job_to_model(job))

    async def save(self, job: Job) -> None:
        model = await self._session.get(JobModel, job.id)
        if model is None:
            self._session.add(_job_to_model(job))
            return
        _apply_job_to_model(job, model)

    async def get_by_id(self, job_id: UUID) -> Job | None:
        model = await self._session.get(JobModel, job_id)
        if model is None:
            return None
        return _job_from_model(model)

    async def get_by_team_and_idempotency_key(
        self,
        *,
        team_id: UUID,
        idempotency_key: str,
    ) -> Job | None:
        statement = select(JobModel).where(
            JobModel.team_id == team_id,
            JobModel.idempotency_key == idempotency_key,
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _job_from_model(model)

    async def claim_next(
        self,
        *,
        queue: str,
        lease_owner: str,
        lease_expires_at: datetime,
        now: datetime,
    ) -> Job | None:
        normalized_queue = normalize_job_queue(queue)
        statement = (
            select(JobModel)
            .where(
                JobModel.queue == normalized_queue.value,
                JobModel.attempt_count < JobModel.max_attempts,
                or_(
                    and_(
                        JobModel.status == JobStatus.PENDING.value,
                        JobModel.available_at <= now,
                    ),
                    and_(
                        JobModel.status == JobStatus.RUNNING.value,
                        JobModel.lease_expires_at.is_not(None),
                        JobModel.lease_expires_at <= now,
                    ),
                ),
            )
            .order_by(JobModel.available_at, JobModel.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        job = _job_from_model(model)
        job.claim(lease_owner=lease_owner, lease_expires_at=lease_expires_at, now=now)
        _apply_job_to_model(job, model)
        return job


def _job_to_model(job: Job) -> JobModel:
    return JobModel(
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


def _apply_job_to_model(job: Job, model: JobModel) -> None:
    model.queue = job.queue.value
    model.job_kind = job.job_kind
    model.status = job.status.value
    model.idempotency_key = job.idempotency_key
    model.payload = dict(job.payload)
    model.attempt_count = job.attempt_count
    model.max_attempts = job.max_attempts
    model.available_at = job.available_at
    model.lease_owner = job.lease_owner
    model.lease_expires_at = job.lease_expires_at
    model.updated_at = job.updated_at
    model.completed_at = job.completed_at
    model.error_code = job.error_code
    model.error_message = job.error_message


def _job_from_model(model: JobModel) -> Job:
    return Job(
        id=model.id,
        team_id=model.team_id,
        queue=JobQueue(model.queue),
        job_kind=model.job_kind,
        status=JobStatus(model.status),
        idempotency_key=model.idempotency_key,
        payload=model.payload,
        attempt_count=model.attempt_count,
        max_attempts=model.max_attempts,
        available_at=model.available_at,
        lease_owner=model.lease_owner,
        lease_expires_at=model.lease_expires_at,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
        completed_at=model.completed_at,
        error_code=model.error_code,
        error_message=model.error_message,
    )
