from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.tools.api.dependencies import RequestAuthenticator
from hify.modules.tools.api.schemas import CreateToolRequest, ToolResponse
from hify.modules.tools.application.commands.create_tool import CreateToolCommand, CreateToolHandler
from hify.modules.tools.application.queries.get_tool import (
    GetToolForActorHandler,
    GetToolForActorQuery,
    ListToolsForActorHandler,
)
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_tools_router(
    *,
    create_tool_handler: CreateToolHandler,
    get_tool_handler: GetToolForActorHandler,
    list_tools_handler: ListToolsForActorHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/tools", tags=["tools"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("", response_model=ToolResponse, status_code=status.HTTP_201_CREATED)
    async def create_tool(
        request: CreateToolRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> ToolResponse:
        try:
            command = CreateToolCommand(
                actor=actor,
                name=request.name,
                description=request.description,
                tool_kind=request.tool_kind,
                input_schema=request.input_schema,
                builtin_name=request.builtin_name,
                endpoint_url=request.endpoint_url,
                http_method=request.http_method,
                http_headers=request.http_headers,
            )
            tool = await create_tool_handler.handle(command)
            return ToolResponse.model_validate(tool)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("", response_model=tuple[ToolResponse, ...])
    async def list_tools(actor: ActorContext = Depends(get_current_actor)) -> tuple[ToolResponse, ...]:
        try:
            tools = await list_tools_handler.handle(actor=actor)
            return tuple(ToolResponse.model_validate(tool) for tool in tools)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/{tool_id}", response_model=ToolResponse)
    async def get_tool(
        tool_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> ToolResponse:
        try:
            tool = await get_tool_handler.handle(GetToolForActorQuery(actor=actor, tool_id=tool_id))
            return ToolResponse.model_validate(tool)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    return router


def _to_http_error(error: HifyError) -> HTTPException:
    if isinstance(error, PermissionDeniedError):
        status_code = status.HTTP_403_FORBIDDEN
    elif isinstance(error, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(error, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    else:
        status_code = status.HTTP_400_BAD_REQUEST

    detail = error.to_detail()
    return HTTPException(
        status_code=status_code,
        detail={
            "code": detail.code,
            "message": detail.message,
            "metadata": detail.metadata,
        },
    )
