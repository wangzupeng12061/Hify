from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from hify.modules.jobs.contracts.dto import ClaimedJob, JobInfo, ScheduleJobRequest


class JobScheduler(Protocol):
    async def schedule_job(self, request: ScheduleJobRequest) -> JobInfo: ...


class JobReader(Protocol):
    async def get_job(self, *, team_id: UUID, job_id: UUID) -> JobInfo: ...


class JobClaimStore(Protocol):
    async def claim_next(
        self,
        *,
        queue: str,
        lease_owner: str,
        lease_seconds: int,
    ) -> ClaimedJob | None: ...

    async def mark_succeeded(self, *, team_id: UUID, job_id: UUID) -> JobInfo: ...

    async def mark_failed(
        self,
        *,
        team_id: UUID,
        job_id: UUID,
        error_code: str,
        error_message: str,
        retry_at: datetime | None = None,
    ) -> JobInfo: ...
