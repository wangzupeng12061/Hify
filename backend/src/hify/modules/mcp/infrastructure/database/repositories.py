from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.mcp.domain.entities import McpDiscoveredTool, McpServer
from hify.modules.mcp.domain.value_objects import McpServerStatus, McpToolStatus, McpTransport
from hify.modules.mcp.infrastructure.database.models import McpDiscoveredToolModel, McpServerModel


class SqlAlchemyMcpServerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, server: McpServer) -> None:
        self._session.add(_server_to_model(server))

    async def save(self, server: McpServer) -> None:
        model = await self._session.get(McpServerModel, server.id)
        if model is None:
            self._session.add(_server_to_model(server))
            return
        _apply_server_to_model(server, model)

    async def get_by_id(self, server_id: UUID) -> McpServer | None:
        model = await self._session.get(McpServerModel, server_id)
        if model is None:
            return None
        return _server_from_model(model)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> McpServer | None:
        statement = select(McpServerModel).where(
            McpServerModel.team_id == team_id,
            func.lower(McpServerModel.name) == name.lower(),
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _server_from_model(model)

    async def list_by_team(self, team_id: UUID) -> tuple[McpServer, ...]:
        statement = (
            select(McpServerModel)
            .where(McpServerModel.team_id == team_id)
            .order_by(McpServerModel.created_at.desc(), McpServerModel.id.desc())
        )
        models = await self._session.scalars(statement)
        return tuple(_server_from_model(model) for model in models)


class SqlAlchemyMcpToolRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tool: McpDiscoveredTool) -> None:
        self._session.add(_tool_to_model(tool))

    async def save(self, tool: McpDiscoveredTool) -> None:
        model = await self._session.get(McpDiscoveredToolModel, tool.id)
        if model is None:
            self._session.add(_tool_to_model(tool))
            return
        _apply_tool_to_model(tool, model)

    async def get_by_id(self, tool_id: UUID) -> McpDiscoveredTool | None:
        model = await self._session.get(McpDiscoveredToolModel, tool_id)
        if model is None:
            return None
        return _tool_from_model(model)

    async def get_by_server_and_name(
        self,
        *,
        server_id: UUID,
        name: str,
    ) -> McpDiscoveredTool | None:
        statement = select(McpDiscoveredToolModel).where(
            McpDiscoveredToolModel.server_id == server_id,
            McpDiscoveredToolModel.name == name,
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _tool_from_model(model)

    async def list_by_server(self, *, team_id: UUID, server_id: UUID) -> tuple[McpDiscoveredTool, ...]:
        statement = (
            select(McpDiscoveredToolModel)
            .where(
                McpDiscoveredToolModel.team_id == team_id,
                McpDiscoveredToolModel.server_id == server_id,
            )
            .order_by(McpDiscoveredToolModel.name, McpDiscoveredToolModel.id)
        )
        models = await self._session.scalars(statement)
        return tuple(_tool_from_model(model) for model in models)


def _server_to_model(server: McpServer) -> McpServerModel:
    return McpServerModel(
        id=server.id,
        team_id=server.team_id,
        name=server.name,
        description=server.description,
        transport=server.transport.value,
        endpoint_url=server.endpoint_url,
        status=server.status.value,
        version=server.version,
        created_by=server.created_by,
        created_at=server.created_at,
        updated_at=server.updated_at,
        last_discovered_at=server.last_discovered_at,
    )


def _apply_server_to_model(server: McpServer, model: McpServerModel) -> None:
    model.name = server.name
    model.description = server.description
    model.transport = server.transport.value
    model.endpoint_url = server.endpoint_url
    model.status = server.status.value
    model.version = server.version
    model.updated_at = server.updated_at
    model.last_discovered_at = server.last_discovered_at


def _server_from_model(model: McpServerModel) -> McpServer:
    return McpServer(
        id=model.id,
        team_id=model.team_id,
        name=model.name,
        description=model.description,
        transport=McpTransport(model.transport),
        endpoint_url=model.endpoint_url,
        status=McpServerStatus(model.status),
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_discovered_at=model.last_discovered_at,
    )


def _tool_to_model(tool: McpDiscoveredTool) -> McpDiscoveredToolModel:
    return McpDiscoveredToolModel(
        id=tool.id,
        team_id=tool.team_id,
        server_id=tool.server_id,
        name=tool.name,
        description=tool.description,
        input_schema=dict(tool.input_schema),
        status=tool.status.value,
        version=tool.version,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
        last_seen_at=tool.last_seen_at,
    )


def _apply_tool_to_model(tool: McpDiscoveredTool, model: McpDiscoveredToolModel) -> None:
    model.name = tool.name
    model.description = tool.description
    model.input_schema = dict(tool.input_schema)
    model.status = tool.status.value
    model.version = tool.version
    model.updated_at = tool.updated_at
    model.last_seen_at = tool.last_seen_at


def _tool_from_model(model: McpDiscoveredToolModel) -> McpDiscoveredTool:
    return McpDiscoveredTool(
        id=model.id,
        team_id=model.team_id,
        server_id=model.server_id,
        name=model.name,
        description=model.description,
        input_schema=model.input_schema,
        status=McpToolStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
        last_seen_at=model.last_seen_at,
    )
