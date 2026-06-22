from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.runs.domain.entities import AgentRun, RunEvent, RunStep


class RunRepository(Protocol):
    async def add(self, run: AgentRun) -> None: ...

    async def save(self, run: AgentRun) -> None: ...

    async def get_by_id(self, run_id: UUID) -> AgentRun | None: ...

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
    ) -> AgentRun | None: ...


class RunStepRepository(Protocol):
    async def add(self, step: RunStep) -> None: ...

    async def get_by_id(self, step_id: UUID) -> RunStep | None: ...

    async def list_by_run(self, *, run_id: UUID) -> tuple[RunStep, ...]: ...


class RunEventRepository(Protocol):
    async def add(self, event: RunEvent) -> None: ...

    async def list_by_run(
        self,
        *,
        run_id: UUID,
        after_sequence_number: int | None,
        limit: int,
    ) -> tuple[RunEvent, ...]: ...
