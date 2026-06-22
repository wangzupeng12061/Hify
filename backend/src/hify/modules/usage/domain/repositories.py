from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.usage.domain.entities import UsageRecord


class UsageRecordRepository(Protocol):
    async def add(self, record: UsageRecord) -> None: ...

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        idempotency_key: str,
    ) -> UsageRecord | None: ...

    async def summarize_for_team(self, *, team_id: UUID) -> tuple[int, int, int, str]: ...

    async def summarize_for_run(self, *, team_id: UUID, run_id: UUID) -> tuple[int, int, int, str]: ...
