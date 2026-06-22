from __future__ import annotations

from datetime import datetime
from uuid import UUID

from hify.modules.jobs.application.commands.mark_job_failed import (
    MarkJobFailedCommand,
    MarkJobFailedHandler,
)
from hify.modules.jobs.application.commands.mark_job_succeeded import (
    MarkJobSucceededCommand,
    MarkJobSucceededHandler,
)
from hify.modules.jobs.application.queries.claim_next_job import (
    ClaimNextJobHandler,
    ClaimNextJobQuery,
)
from hify.modules.jobs.contracts.dto import ClaimedJob, JobInfo
from hify.modules.jobs.contracts.services import JobClaimStore


class JobClaimStoreService(JobClaimStore):
    def __init__(
        self,
        claim_next_job_handler: ClaimNextJobHandler,
        mark_succeeded_handler: MarkJobSucceededHandler,
        mark_failed_handler: MarkJobFailedHandler,
    ) -> None:
        self._claim_next_job_handler = claim_next_job_handler
        self._mark_succeeded_handler = mark_succeeded_handler
        self._mark_failed_handler = mark_failed_handler

    async def claim_next(
        self,
        *,
        queue: str,
        lease_owner: str,
        lease_seconds: int,
    ) -> ClaimedJob | None:
        return await self._claim_next_job_handler.handle(
            ClaimNextJobQuery(
                queue=queue,
                lease_owner=lease_owner,
                lease_seconds=lease_seconds,
            )
        )

    async def mark_succeeded(self, *, team_id: UUID, job_id: UUID) -> JobInfo:
        return await self._mark_succeeded_handler.handle(
            MarkJobSucceededCommand(team_id=team_id, job_id=job_id)
        )

    async def mark_failed(
        self,
        *,
        team_id: UUID,
        job_id: UUID,
        error_code: str,
        error_message: str,
        retry_at: datetime | None = None,
    ) -> JobInfo:
        return await self._mark_failed_handler.handle(
            MarkJobFailedCommand(
                team_id=team_id,
                job_id=job_id,
                error_code=error_code,
                error_message=error_message,
                retry_at=retry_at,
            )
        )
