from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.application.commands.create_server import (
    CreateMcpServerCommand,
    CreateMcpServerHandler,
)
from hify.modules.mcp.application.commands.refresh_tools import (
    McpToolDiscoveryService,
    RefreshMcpToolsCommand,
    RefreshMcpToolsHandler,
)
from hify.modules.mcp.application.invoker import McpToolInvokerService
from hify.modules.mcp.application.queries.get_server import (
    GetMcpServerForActorQuery,
    GetMcpServerForActorHandler,
    GetMcpServerHandler,
    ListMcpServersForActorHandler,
    McpServerCatalogService,
)
from hify.modules.mcp.application.queries.list_tools import (
    ListMcpToolsForActorHandler,
    ListMcpToolsForActorQuery,
)
from hify.modules.mcp.contracts.dto import (
    DiscoveredMcpTool,
    McpToolInvocationRequest,
    McpToolInvocationResult,
)
from hify.modules.mcp.domain.entities import McpDiscoveredTool, McpServer
from hify.modules.mcp.domain.errors import (
    McpPermissionDeniedError,
    McpServerAlreadyExistsError,
)
from hify.shared.domain.clock import Clock


NOW = datetime(2026, 6, 22, tzinfo=UTC)
TEAM_ID = UUID("00000000-0000-7000-8000-000000000001")
USER_ID = UUID("00000000-0000-7000-8000-000000000002")
MEMBERSHIP_ID = UUID("00000000-0000-7000-8000-000000000003")


class FixedClock(Clock):
    def now(self) -> datetime:
        return NOW


class FakeMcpServerRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, McpServer] = {}

    async def add(self, server: McpServer) -> None:
        self.items[server.id] = server

    async def save(self, server: McpServer) -> None:
        self.items[server.id] = server

    async def get_by_id(self, server_id: UUID) -> McpServer | None:
        return self.items.get(server_id)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> McpServer | None:
        for server in self.items.values():
            if server.team_id == team_id and server.name.lower() == name.lower():
                return server
        return None

    async def list_by_team(self, team_id: UUID) -> tuple[McpServer, ...]:
        servers = [server for server in self.items.values() if server.team_id == team_id]
        return tuple(sorted(servers, key=lambda server: (server.created_at, server.id), reverse=True))


class FakeMcpToolRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, McpDiscoveredTool] = {}

    async def add(self, tool: McpDiscoveredTool) -> None:
        self.items[tool.id] = tool

    async def save(self, tool: McpDiscoveredTool) -> None:
        self.items[tool.id] = tool

    async def get_by_id(self, tool_id: UUID) -> McpDiscoveredTool | None:
        return self.items.get(tool_id)

    async def get_by_server_and_name(
        self,
        *,
        server_id: UUID,
        name: str,
    ) -> McpDiscoveredTool | None:
        for tool in self.items.values():
            if tool.server_id == server_id and tool.name == name:
                return tool
        return None

    async def list_by_server(self, *, team_id: UUID, server_id: UUID) -> tuple[McpDiscoveredTool, ...]:
        tools = [
            tool
            for tool in self.items.values()
            if tool.team_id == team_id and tool.server_id == server_id
        ]
        return tuple(sorted(tools, key=lambda tool: (tool.name, tool.id)))


class FakeMcpUnitOfWork:
    def __init__(self) -> None:
        self.servers = FakeMcpServerRepository()
        self.tools = FakeMcpToolRepository()
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


class RecordingMcpClient:
    def __init__(self) -> None:
        self.tools = (
            DiscoveredMcpTool(
                name="search",
                description="Search docs",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            ),
        )
        self.requests: list[McpToolInvocationRequest] = []

    async def list_tools(self, server: McpServer) -> tuple[DiscoveredMcpTool, ...]:
        _ = server
        return self.tools

    async def call_tool(
        self,
        server: McpServer,
        tool_name: str,
        request: McpToolInvocationRequest,
    ) -> McpToolInvocationResult:
        _ = server, tool_name
        self.requests.append(request)
        return McpToolInvocationResult(
            tool_call_id=request.tool_call_id,
            content="search result",
            metadata={"tool": tool_name},
        )


def actor_with_mcp_permissions() -> ActorContext:
    return ActorContext(
        user_id=USER_ID,
        team_id=TEAM_ID,
        membership_id=MEMBERSHIP_ID,
        role="admin",
        permissions=("mcp.manage", "mcp.read"),
    )


@pytest.mark.asyncio
async def test_create_mcp_server_and_catalog_queries() -> None:
    unit_of_work = FakeMcpUnitOfWork()
    actor = actor_with_mcp_permissions()
    created = await CreateMcpServerHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateMcpServerCommand(
            actor=actor,
            name="Docs",
            description=None,
            transport="streamable_http",
            endpoint_url="https://mcp.example.com/mcp",
        )
    )
    catalog = McpServerCatalogService(lambda: unit_of_work)

    listed_for_actor = await ListMcpServersForActorHandler(lambda: unit_of_work).handle(actor=actor)
    listed_by_catalog = await catalog.list_servers(team_id=actor.team_id)
    fetched_by_actor = await GetMcpServerForActorHandler(
        GetMcpServerHandler(lambda: unit_of_work)
    ).handle(
        GetMcpServerForActorQuery(actor=actor, server_id=created.id)
    )

    assert created.name == "Docs"
    assert listed_for_actor == (created,)
    assert listed_by_catalog == (created,)
    assert fetched_by_actor == created
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_create_mcp_server_rejects_duplicate_name() -> None:
    unit_of_work = FakeMcpUnitOfWork()
    actor = actor_with_mcp_permissions()
    handler = CreateMcpServerHandler(lambda: unit_of_work, FixedClock())
    command = CreateMcpServerCommand(
        actor=actor,
        name="Docs",
        description=None,
        transport="streamable_http",
        endpoint_url="https://mcp.example.com/mcp",
    )

    await handler.handle(command)
    with pytest.raises(McpServerAlreadyExistsError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_create_mcp_server_requires_manage_permission() -> None:
    actor = ActorContext(
        user_id=USER_ID,
        team_id=TEAM_ID,
        membership_id=MEMBERSHIP_ID,
        role="viewer",
        permissions=("mcp.read",),
    )
    handler = CreateMcpServerHandler(lambda: FakeMcpUnitOfWork(), FixedClock())

    with pytest.raises(McpPermissionDeniedError):
        await handler.handle(
            CreateMcpServerCommand(
                actor=actor,
                name="Docs",
                description=None,
                transport="streamable_http",
                endpoint_url="https://mcp.example.com/mcp",
            )
        )


@pytest.mark.asyncio
async def test_refresh_tools_upserts_discovered_tools() -> None:
    unit_of_work = FakeMcpUnitOfWork()
    actor = actor_with_mcp_permissions()
    client = RecordingMcpClient()
    server = await CreateMcpServerHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateMcpServerCommand(
            actor=actor,
            name="Docs",
            description=None,
            transport="streamable_http",
            endpoint_url="https://mcp.example.com/mcp",
        )
    )
    handler = RefreshMcpToolsHandler(lambda: unit_of_work, client, FixedClock())

    first = await handler.handle(RefreshMcpToolsCommand(actor=actor, server_id=server.id))
    second = await handler.handle(RefreshMcpToolsCommand(actor=actor, server_id=server.id))
    listed = await ListMcpToolsForActorHandler(lambda: unit_of_work).handle(
        ListMcpToolsForActorQuery(actor=actor, server_id=server.id)
    )
    discovery = McpToolDiscoveryService(lambda: unit_of_work, handler)

    assert len(first) == 1
    assert second[0].id == first[0].id
    assert listed == second
    assert await discovery.list_tools(team_id=actor.team_id, server_id=server.id) == second


@pytest.mark.asyncio
async def test_mcp_tool_invoker_calls_client_with_cached_tool() -> None:
    unit_of_work = FakeMcpUnitOfWork()
    actor = actor_with_mcp_permissions()
    client = RecordingMcpClient()
    server = await CreateMcpServerHandler(lambda: unit_of_work, FixedClock()).handle(
        CreateMcpServerCommand(
            actor=actor,
            name="Docs",
            description=None,
            transport="streamable_http",
            endpoint_url="https://mcp.example.com/mcp",
        )
    )
    tools = await RefreshMcpToolsHandler(lambda: unit_of_work, client, FixedClock()).handle(
        RefreshMcpToolsCommand(actor=actor, server_id=server.id)
    )
    request = McpToolInvocationRequest(
        team_id=actor.team_id,
        server_id=server.id,
        tool_id=tools[0].id,
        tool_call_id=UUID("00000000-0000-7000-8000-000000000010"),
        arguments={"query": "hify"},
    )

    result = await McpToolInvokerService(lambda: unit_of_work, client).invoke_tool(request)

    assert result.content == "search result"
    assert client.requests == [request]
