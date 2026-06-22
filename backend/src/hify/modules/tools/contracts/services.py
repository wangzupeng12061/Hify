from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.tools.contracts.dto import (
    ToolExecutionRequest,
    ToolExecutionResult,
    ToolInfo,
)


class ToolCatalog(Protocol):
    async def get_tool(self, *, team_id: UUID, tool_id: UUID) -> ToolInfo: ...

    async def list_tools(self, *, team_id: UUID) -> tuple[ToolInfo, ...]: ...


class ToolExecutor(Protocol):
    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult: ...
