from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.tools.domain.entities import ToolDefinition
from hify.modules.tools.domain.value_objects import HttpToolMethod, ToolKind, ToolStatus
from hify.modules.tools.infrastructure.database.models import ToolDefinitionModel


class SqlAlchemyToolDefinitionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, tool: ToolDefinition) -> None:
        self._session.add(_tool_to_model(tool))

    async def get_by_id(self, tool_id: UUID) -> ToolDefinition | None:
        model = await self._session.get(ToolDefinitionModel, tool_id)
        if model is None:
            return None
        return _tool_from_model(model)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> ToolDefinition | None:
        statement = select(ToolDefinitionModel).where(
            ToolDefinitionModel.team_id == team_id,
            func.lower(ToolDefinitionModel.name) == name.lower(),
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _tool_from_model(model)

    async def list_by_team(self, team_id: UUID) -> tuple[ToolDefinition, ...]:
        statement = (
            select(ToolDefinitionModel)
            .where(ToolDefinitionModel.team_id == team_id)
            .order_by(ToolDefinitionModel.created_at.desc(), ToolDefinitionModel.id.desc())
        )
        models = await self._session.scalars(statement)
        return tuple(_tool_from_model(model) for model in models)


def _tool_to_model(tool: ToolDefinition) -> ToolDefinitionModel:
    return ToolDefinitionModel(
        id=tool.id,
        team_id=tool.team_id,
        name=tool.name,
        description=tool.description,
        tool_kind=tool.tool_kind.value,
        status=tool.status.value,
        input_schema=dict(tool.input_schema),
        builtin_name=tool.builtin_name,
        endpoint_url=tool.endpoint_url,
        http_method=tool.http_method.value if tool.http_method is not None else None,
        http_headers=dict(tool.http_headers),
        mcp_server_id=tool.mcp_server_id,
        mcp_tool_id=tool.mcp_tool_id,
        mcp_tool_name=tool.mcp_tool_name,
        version=tool.version,
        created_by=tool.created_by,
        created_at=tool.created_at,
        updated_at=tool.updated_at,
    )


def _tool_from_model(model: ToolDefinitionModel) -> ToolDefinition:
    return ToolDefinition(
        id=model.id,
        team_id=model.team_id,
        name=model.name,
        description=model.description,
        tool_kind=ToolKind(model.tool_kind),
        status=ToolStatus(model.status),
        input_schema=model.input_schema,
        builtin_name=model.builtin_name,
        endpoint_url=model.endpoint_url,
        http_method=HttpToolMethod(model.http_method) if model.http_method is not None else None,
        http_headers=model.http_headers,
        mcp_server_id=model.mcp_server_id,
        mcp_tool_id=model.mcp_tool_id,
        mcp_tool_name=model.mcp_tool_name,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
