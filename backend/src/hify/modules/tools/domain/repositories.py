from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.tools.domain.entities import ToolDefinition


class ToolDefinitionRepository(Protocol):
    async def add(self, tool: ToolDefinition) -> None: ...

    async def get_by_id(self, tool_id: UUID) -> ToolDefinition | None: ...

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> ToolDefinition | None: ...

    async def list_by_team(self, team_id: UUID) -> tuple[ToolDefinition, ...]: ...
