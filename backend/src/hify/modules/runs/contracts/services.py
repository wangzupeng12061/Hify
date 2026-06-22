from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.runs.contracts.dto import RunEventPage, RunInfo


class RunReader(Protocol):
    async def get_run(self, *, team_id: UUID, run_id: UUID) -> RunInfo: ...

    async def list_events(
        self,
        *,
        team_id: UUID,
        run_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> RunEventPage: ...
