from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from hify.modules.jobs.application.dto import job_info_from_domain
from hify.modules.jobs.application.ports import JobsUnitOfWorkFactory
from hify.modules.jobs.contracts.dto import JobInfo, ScheduleJobRequest
from hify.modules.jobs.contracts.services import JobScheduler
from hify.modules.jobs.domain.entities import Job
from hify.modules.jobs.domain.value_objects import normalize_idempotency_key
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class ScheduleJobCommand:
    team_id: UUID
    queue: str
    job_kind: str
    idempotency_key: str
    payload: Mapping[str, object]
    created_by: UUID
    available_at: datetime | None = None
    max_attempts: int = 3


class ScheduleJobHandler:
    def __init__(self, unit_of_work_factory: JobsUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: ScheduleJobCommand) -> JobInfo:
        idempotency_key = normalize_idempotency_key(command.idempotency_key)
        async with self._unit_of_work_factory() as unit_of_work:
            existing = await unit_of_work.jobs.get_by_team_and_idempotency_key(
                team_id=command.team_id,
                idempotency_key=idempotency_key,
            )
            if existing is not None:
                return job_info_from_domain(existing)

            now = self._clock.now()
            job = Job.create(
                team_id=command.team_id,
                queue=command.queue,
                job_kind=command.job_kind,
                idempotency_key=idempotency_key,
                payload=command.payload,
                max_attempts=command.max_attempts,
                available_at=command.available_at,
                created_by=command.created_by,
                now=now,
            )
            await unit_of_work.jobs.add(job)
            await unit_of_work.commit()
            return job_info_from_domain(job)


class JobSchedulerService(JobScheduler):
    def __init__(self, handler: ScheduleJobHandler) -> None:
        self._handler = handler

    async def schedule_job(self, request: ScheduleJobRequest) -> JobInfo:
        return await self._handler.handle(
            ScheduleJobCommand(
                team_id=request.team_id,
                queue=request.queue,
                job_kind=request.job_kind,
                idempotency_key=request.idempotency_key,
                payload=request.payload,
                created_by=request.created_by,
                available_at=request.available_at,
                max_attempts=request.max_attempts,
            )
        )
