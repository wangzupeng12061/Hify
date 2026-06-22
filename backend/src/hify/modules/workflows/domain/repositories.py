from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.workflows.domain.entities import Workflow, WorkflowVersion


class WorkflowRepository(Protocol):
    async def add(self, workflow: Workflow) -> None: ...

    async def save(self, workflow: Workflow) -> None: ...

    async def get_by_id(self, workflow_id: UUID) -> Workflow | None: ...

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> Workflow | None: ...


class WorkflowVersionRepository(Protocol):
    async def add(self, workflow_version: WorkflowVersion) -> None: ...

    async def get_by_id(self, workflow_version_id: UUID) -> WorkflowVersion | None: ...

    async def get_latest_by_workflow_id(self, workflow_id: UUID) -> WorkflowVersion | None: ...
