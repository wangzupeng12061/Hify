from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.workflows.contracts.dto import WorkflowVersionInfo


class WorkflowCatalog(Protocol):
    async def get_latest_published_version(
        self,
        *,
        team_id: UUID,
        workflow_id: UUID,
    ) -> WorkflowVersionInfo: ...

    async def get_workflow_version(
        self,
        *,
        team_id: UUID,
        workflow_version_id: UUID,
    ) -> WorkflowVersionInfo: ...
