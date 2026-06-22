from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.tools.application.commands.create_tool import CreateToolCommand, CreateToolHandler
from hify.modules.tools.application.queries.get_tool import (
    GetToolForActorHandler,
    GetToolForActorQuery,
    GetToolHandler,
    ListToolsForActorHandler,
    ToolCatalogService,
)
from hify.modules.tools.domain.entities import ToolDefinition
from hify.modules.tools.domain.errors import ToolAlreadyExistsError, ToolPermissionDeniedError
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


def actor_with_tool_permissions() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="member",
        permissions=("tools.manage", "tools.read"),
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
