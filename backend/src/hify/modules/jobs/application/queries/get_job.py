from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.jobs.application.authorization import require_read_jobs
from hify.modules.jobs.application.dto import job_info_from_domain
from hify.modules.jobs.application.ports import JobsUnitOfWorkFactory
from hify.modules.jobs.contracts.dto import JobInfo
from hify.modules.jobs.contracts.services import JobReader
from hify.modules.jobs.domain.errors import JobNotFoundError


@dataclass(frozen=True, slots=True)
class GetJobForActorQuery:
    actor: ActorContext
    job_id: UUID


class GetJobForActorHandler:
    def __init__(self, unit_of_work_factory: JobsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetJobForActorQuery) -> JobInfo:
        require_read_jobs(query.actor)
        async with self._unit_of_work_factory() as unit_of_work:
            job = await unit_of_work.jobs.get_by_id(query.job_id)
        if job is None or job.team_id != query.actor.team_id:
            raise JobNotFoundError("job was not found")
        return job_info_from_domain(job)


class JobReaderService(JobReader):
    def __init__(self, unit_of_work_factory: JobsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def get_job(self, *, team_id: UUID, job_id: UUID) -> JobInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            job = await unit_of_work.jobs.get_by_id(job_id)
        if job is None or job.team_id != team_id:
            raise JobNotFoundError("job was not found")
        return job_info_from_domain(job)
