from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from hify.modules.jobs.domain.entities import Job


class JobRepository(Protocol):
    async def add(self, job: Job) -> None: ...

    async def save(self, job: Job) -> None: ...

    async def get_by_id(self, job_id: UUID) -> Job | None: ...

    async def get_by_team_and_idempotency_key(
        self,
        *,
        team_id: UUID,
        idempotency_key: str,
    ) -> Job | None: ...

    async def claim_next(
        self,
        *,
        queue: str,
        lease_owner: str,
        lease_expires_at: datetime,
        now: datetime,
    ) -> Job | None: ...
