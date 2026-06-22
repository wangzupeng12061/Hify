from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.jobs.application.dto import job_info_from_domain
from hify.modules.jobs.application.ports import JobsUnitOfWorkFactory
from hify.modules.jobs.contracts.dto import JobInfo
from hify.modules.jobs.domain.errors import JobNotFoundError
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class MarkJobSucceededCommand:
    team_id: UUID
    job_id: UUID


class MarkJobSucceededHandler:
    def __init__(self, unit_of_work_factory: JobsUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: MarkJobSucceededCommand) -> JobInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            job = await unit_of_work.jobs.get_by_id(command.job_id)
            if job is None or job.team_id != command.team_id:
                raise JobNotFoundError("job was not found")
            job.mark_succeeded(now=self._clock.now())
            await unit_of_work.jobs.save(job)
            await unit_of_work.commit()
            return job_info_from_domain(job)
