from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Mapping
from typing import Protocol, Self
from uuid import UUID

from hify.modules.tools.contracts.dto import ToolExecutionResult
from hify.modules.tools.domain.repositories import ToolDefinitionRepository
from hify.shared.application.uow import UnitOfWork


class ToolsUnitOfWork(UnitOfWork, Protocol):
    tools: ToolDefinitionRepository

    async def __aenter__(self) -> Self: ...


ToolsUnitOfWorkFactory = Callable[[], ToolsUnitOfWork]


@dataclass(frozen=True, slots=True)
class BuiltinToolInvocation:
    team_id: UUID
    tool_id: UUID
    tool_call_id: UUID
    builtin_name: str
    arguments: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class HttpToolInvocation:
    team_id: UUID
    tool_id: UUID
    tool_call_id: UUID
    endpoint_url: str
    http_method: str
    http_headers: Mapping[str, str]
    arguments: Mapping[str, object]


class BuiltinToolInvoker(Protocol):
    async def invoke_builtin_tool(self, invocation: BuiltinToolInvocation) -> ToolExecutionResult: ...


class HttpToolInvoker(Protocol):
    async def invoke_http_tool(self, invocation: HttpToolInvocation) -> ToolExecutionResult: ...
