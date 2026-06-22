from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from hify.modules.jobs.application.dto import job_info_from_domain
from hify.modules.jobs.application.ports import JobsUnitOfWorkFactory
from hify.modules.jobs.contracts.dto import ClaimedJob
from hify.modules.jobs.domain.errors import JobValidationError
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class ClaimNextJobQuery:
    queue: str
    lease_owner: str
    lease_seconds: int


class ClaimNextJobHandler:
    def __init__(self, unit_of_work_factory: JobsUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, query: ClaimNextJobQuery) -> ClaimedJob | None:
        if query.lease_seconds < 1 or query.lease_seconds > 3600:
            raise JobValidationError("job lease seconds must be between 1 and 3600")
        now = self._clock.now()
        lease_expires_at = now + timedelta(seconds=query.lease_seconds)
        async with self._unit_of_work_factory() as unit_of_work:
            job = await unit_of_work.jobs.claim_next(
                queue=query.queue,
                lease_owner=query.lease_owner,
                lease_expires_at=lease_expires_at,
                now=now,
            )
            if job is None:
                return None
            await unit_of_work.commit()
            return ClaimedJob(
                job=job_info_from_domain(job),
                lease_owner=query.lease_owner,
                lease_expires_at=lease_expires_at,
            )
