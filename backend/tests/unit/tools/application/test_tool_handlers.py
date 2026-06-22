from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.contracts.dto import (
    McpToolInfo,
    McpToolInvocationRequest,
    McpToolInvocationResult,
)
from hify.modules.tools.application.commands.create_tool import CreateToolCommand, CreateToolHandler
from hify.modules.tools.application.executor import ToolRuntimeExecutor
from hify.modules.tools.application.ports import BuiltinToolInvocation, HttpToolInvocation
from hify.modules.tools.application.queries.get_tool import (
    GetToolForActorHandler,
    GetToolForActorQuery,
    GetToolHandler,
    ListToolsForActorHandler,
    ToolCatalogService,
)
from hify.modules.tools.contracts.dto import ToolExecutionRequest, ToolExecutionResult
from hify.modules.tools.domain.entities import ToolDefinition
from hify.modules.tools.domain.errors import (
    ToolAlreadyExistsError,
    ToolDisabledError,
    ToolPermissionDeniedError,
    ToolValidationError,
)
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeToolRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, ToolDefinition] = {}

    async def add(self, tool: ToolDefinition) -> None:
        self.items[tool.id] = tool

    async def get_by_id(self, tool_id: UUID) -> ToolDefinition | None:
        return self.items.get(tool_id)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> ToolDefinition | None:
        for tool in self.items.values():
            if tool.team_id == team_id and tool.name.lower() == name.lower():
                return tool
        return None

    async def list_by_team(self, team_id: UUID) -> tuple[ToolDefinition, ...]:
        tools = [tool for tool in self.items.values() if tool.team_id == team_id]
        return tuple(sorted(tools, key=lambda tool: (tool.created_at, tool.id), reverse=True))


class FakeToolsUnitOfWork:
    def __init__(self) -> None:
        self.tools = FakeToolRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


class RecordingBuiltinToolInvoker:
    def __init__(self) -> None:
        self.invocations: list[BuiltinToolInvocation] = []

    async def invoke_builtin_tool(self, invocation: BuiltinToolInvocation) -> ToolExecutionResult:
        self.invocations.append(invocation)
        return ToolExecutionResult(
            tool_call_id=invocation.tool_call_id,
            content="builtin result",
            metadata={"builtin_name": invocation.builtin_name},
        )


class RecordingHttpToolInvoker:
    def __init__(self) -> None:
        self.invocations: list[HttpToolInvocation] = []

    async def invoke_http_tool(self, invocation: HttpToolInvocation) -> ToolExecutionResult:
        self.invocations.append(invocation)
        return ToolExecutionResult(
            tool_call_id=invocation.tool_call_id,
            content="http result",
            metadata={"endpoint_url": invocation.endpoint_url},
        )


class FakeMcpToolDiscovery:
    def __init__(self, tool: McpToolInfo | None = None) -> None:
        self.tool = tool or mcp_tool_info()

    async def get_tool(self, *, team_id: UUID, tool_id: UUID) -> McpToolInfo:
        if self.tool.team_id != team_id or self.tool.id != tool_id:
            raise AssertionError("unexpected mcp tool lookup")
        return self.tool

    async def list_tools(self, *, team_id: UUID, server_id: UUID) -> tuple[McpToolInfo, ...]:
        _ = team_id, server_id
        return (self.tool,)

    async def refresh_tools(self, *, team_id: UUID, server_id: UUID) -> tuple[McpToolInfo, ...]:
        _ = team_id, server_id
        return (self.tool,)


class RecordingMcpToolInvoker:
    def __init__(self) -> None:
        self.requests: list[McpToolInvocationRequest] = []

    async def invoke_tool(self, request: McpToolInvocationRequest) -> McpToolInvocationResult:
        self.requests.append(request)
        return McpToolInvocationResult(
            tool_call_id=request.tool_call_id,
            content="mcp result",
            metadata={"mcp_tool_id": str(request.tool_id)},
        )


def actor_with_tool_permissions() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="member",
        permissions=("tools.manage", "tools.read"),
    )


def mcp_tool_info(status: str = "active") -> McpToolInfo:
    return McpToolInfo(
        id=UUID("00000000-0000-7000-8000-000000000020"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        server_id=UUID("00000000-0000-7000-8000-000000000021"),
        name="search_docs",
        description="Search MCP docs",
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
        status=status,
        created_at=FixedClock().now(),
        updated_at=FixedClock().now(),
        last_seen_at=FixedClock().now(),
    )


@pytest.mark.asyncio
async def test_create_http_tool_definition() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    handler = CreateToolHandler(lambda: unit_of_work, FixedClock())

    tool = await handler.handle(
        CreateToolCommand(
            actor=actor,
            name="CRM Lookup",
            description="Find customer records",
            tool_kind="http",
            input_schema={"type": "object", "properties": {}},
            builtin_name=None,
            endpoint_url="https://crm.example.com/search",
            http_method="POST",
            http_headers={"X-Hify-Tool": "crm"},
        )
    )

    assert tool.name == "CRM Lookup"
    assert tool.tool_kind == "http"
    assert tool.http_method == "POST"
    assert tool.http_headers == {"X-Hify-Tool": "crm"}
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_create_mcp_tool_uses_discovered_tool_snapshot() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    discovered_tool = mcp_tool_info()
    handler = CreateToolHandler(
        lambda: unit_of_work,
        FixedClock(),
        FakeMcpToolDiscovery(discovered_tool),
    )

    tool = await handler.handle(
        CreateToolCommand(
            actor=actor,
            name="Docs Search",
            description=None,
            tool_kind="mcp",
            input_schema={"type": "object"},
            builtin_name=None,
            endpoint_url=None,
            http_method=None,
            http_headers={},
            mcp_server_id=discovered_tool.server_id,
            mcp_tool_id=discovered_tool.id,
        )
    )

    assert tool.tool_kind == "mcp"
    assert tool.input_schema == discovered_tool.input_schema
    assert tool.mcp_server_id == discovered_tool.server_id
    assert tool.mcp_tool_id == discovered_tool.id
    assert tool.mcp_tool_name == discovered_tool.name


@pytest.mark.asyncio
async def test_create_mcp_tool_rejects_inactive_discovered_tool() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    discovered_tool = mcp_tool_info(status="disabled")
    handler = CreateToolHandler(
        lambda: unit_of_work,
        FixedClock(),
        FakeMcpToolDiscovery(discovered_tool),
    )

    with pytest.raises(ToolValidationError):
        await handler.handle(
            CreateToolCommand(
                actor=actor,
                name="Docs Search",
                description=None,
                tool_kind="mcp",
                input_schema={"type": "object"},
                builtin_name=None,
                endpoint_url=None,
                http_method=None,
                http_headers={},
                mcp_server_id=discovered_tool.server_id,
                mcp_tool_id=discovered_tool.id,
            )
        )


@pytest.mark.asyncio
async def test_create_tool_rejects_duplicate_name() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    handler = CreateToolHandler(lambda: unit_of_work, FixedClock())
    command = CreateToolCommand(
        actor=actor,
        name="Search",
        description=None,
        tool_kind="builtin",
        input_schema={"type": "object"},
        builtin_name="web.search",
        endpoint_url=None,
        http_method=None,
        http_headers={},
    )

    await handler.handle(command)
    with pytest.raises(ToolAlreadyExistsError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_create_tool_requires_manage_permission() -> None:
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=("tools.read",),
    )
    handler = CreateToolHandler(lambda: FakeToolsUnitOfWork(), FixedClock())

    with pytest.raises(ToolPermissionDeniedError):
        await handler.handle(
            CreateToolCommand(
                actor=actor,
                name="Search",
                description=None,
                tool_kind="builtin",
                input_schema={"type": "object"},
                builtin_name="web.search",
                endpoint_url=None,
                http_method=None,
                http_headers={},
            )
        )


@pytest.mark.asyncio
async def test_tool_catalog_and_actor_queries_return_team_tools() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    created = await CreateToolHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateToolCommand(
            actor=actor,
            name="Search",
            description=None,
            tool_kind="builtin",
            input_schema={"type": "object"},
            builtin_name="web.search",
            endpoint_url=None,
            http_method=None,
            http_headers={},
        )
    )
    get_tool_handler = GetToolHandler(lambda: unit_of_work)
    catalog = ToolCatalogService(get_tool_handler, lambda: unit_of_work)

    fetched = await GetToolForActorHandler(get_tool_handler).handle(
        GetToolForActorQuery(actor=actor, tool_id=created.id)
    )
    listed = await ListToolsForActorHandler(lambda: unit_of_work).handle(actor=actor)
    catalog_tool = await catalog.get_tool(team_id=actor.team_id, tool_id=created.id)

    assert fetched == created
    assert listed == (created,)
    assert catalog_tool == created


@pytest.mark.asyncio
async def test_tool_executor_invokes_http_tool() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    tool = await CreateToolHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateToolCommand(
            actor=actor,
            name="CRM Lookup",
            description=None,
            tool_kind="http",
            input_schema={
                "type": "object",
                "required": ["email"],
                "properties": {"email": {"type": "string"}},
            },
            builtin_name=None,
            endpoint_url="https://crm.example.com/search",
            http_method="POST",
            http_headers={"X-Hify-Tool": "crm"},
        )
    )
    http_invoker = RecordingHttpToolInvoker()
    executor = ToolRuntimeExecutor(
        lambda: unit_of_work,
        RecordingBuiltinToolInvoker(),
        http_invoker,
        RecordingMcpToolInvoker(),
    )
    request = ToolExecutionRequest(
        team_id=actor.team_id,
        tool_id=tool.id,
        tool_call_id=UUID("00000000-0000-7000-8000-000000000010"),
        arguments={"email": "owner@example.com"},
    )

    result = await executor.execute_tool(request)

    assert result.content == "http result"
    assert http_invoker.invocations[0].http_method == "POST"
    assert http_invoker.invocations[0].arguments == {"email": "owner@example.com"}


@pytest.mark.asyncio
async def test_tool_executor_invokes_builtin_tool() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    tool = await CreateToolHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateToolCommand(
            actor=actor,
            name="Search",
            description=None,
            tool_kind="builtin",
            input_schema={"type": "object"},
            builtin_name="web.search",
            endpoint_url=None,
            http_method=None,
            http_headers={},
        )
    )
    builtin_invoker = RecordingBuiltinToolInvoker()
    executor = ToolRuntimeExecutor(
        lambda: unit_of_work,
        builtin_invoker,
        RecordingHttpToolInvoker(),
        RecordingMcpToolInvoker(),
    )

    result = await executor.execute_tool(
        ToolExecutionRequest(
            team_id=actor.team_id,
            tool_id=tool.id,
            tool_call_id=UUID("00000000-0000-7000-8000-000000000010"),
            arguments={"query": "hify"},
        )
    )

    assert result.content == "builtin result"
    assert builtin_invoker.invocations[0].builtin_name == "web.search"


@pytest.mark.asyncio
async def test_tool_executor_invokes_mcp_tool() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    discovered_tool = mcp_tool_info()
    tool = await CreateToolHandler(
        lambda: unit_of_work,
        FixedClock(),
        FakeMcpToolDiscovery(discovered_tool),
    ).handle(
        CreateToolCommand(
            actor=actor,
            name="Docs Search",
            description=None,
            tool_kind="mcp",
            input_schema={"type": "object"},
            builtin_name=None,
            endpoint_url=None,
            http_method=None,
            http_headers={},
            mcp_server_id=discovered_tool.server_id,
            mcp_tool_id=discovered_tool.id,
        )
    )
    mcp_invoker = RecordingMcpToolInvoker()
    executor = ToolRuntimeExecutor(
        lambda: unit_of_work,
        RecordingBuiltinToolInvoker(),
        RecordingHttpToolInvoker(),
        mcp_invoker,
    )
    request = ToolExecutionRequest(
        team_id=actor.team_id,
        tool_id=tool.id,
        tool_call_id=UUID("00000000-0000-7000-8000-000000000010"),
        arguments={"query": "hify"},
    )

    result = await executor.execute_tool(request)

    assert result.content == "mcp result"
    assert mcp_invoker.requests[0].server_id == discovered_tool.server_id
    assert mcp_invoker.requests[0].tool_id == discovered_tool.id


@pytest.mark.asyncio
async def test_tool_executor_rejects_invalid_arguments() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    tool = await CreateToolHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateToolCommand(
            actor=actor,
            name="CRM Lookup",
            description=None,
            tool_kind="http",
            input_schema={
                "type": "object",
                "required": ["email"],
                "properties": {"email": {"type": "string"}},
            },
            builtin_name=None,
            endpoint_url="https://crm.example.com/search",
            http_method="POST",
            http_headers={},
        )
    )
    executor = ToolRuntimeExecutor(
        lambda: unit_of_work,
        RecordingBuiltinToolInvoker(),
        RecordingHttpToolInvoker(),
        RecordingMcpToolInvoker(),
    )

    with pytest.raises(ToolValidationError):
        await executor.execute_tool(
            ToolExecutionRequest(
                team_id=actor.team_id,
                tool_id=tool.id,
                tool_call_id=UUID("00000000-0000-7000-8000-000000000010"),
                arguments={"email": 123},
            )
        )


@pytest.mark.asyncio
async def test_tool_executor_rejects_disabled_tool() -> None:
    unit_of_work = FakeToolsUnitOfWork()
    actor = actor_with_tool_permissions()
    tool_info = await CreateToolHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateToolCommand(
            actor=actor,
            name="Search",
            description=None,
            tool_kind="builtin",
            input_schema={"type": "object"},
            builtin_name="web.search",
            endpoint_url=None,
            http_method=None,
            http_headers={},
        )
    )
    tool = await unit_of_work.tools.get_by_id(tool_info.id)
    assert tool is not None
    tool.disable(now=FixedClock().now())

    executor = ToolRuntimeExecutor(
        lambda: unit_of_work,
        RecordingBuiltinToolInvoker(),
        RecordingHttpToolInvoker(),
        RecordingMcpToolInvoker(),
    )

    with pytest.raises(ToolDisabledError):
        await executor.execute_tool(
            ToolExecutionRequest(
                team_id=actor.team_id,
                tool_id=tool_info.id,
                tool_call_id=UUID("00000000-0000-7000-8000-000000000010"),
                arguments={},
            )
        )
