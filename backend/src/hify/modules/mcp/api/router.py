from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.mcp.api.dependencies import RequestAuthenticator
from hify.modules.mcp.api.schemas import (
    CreateMcpServerRequest,
    McpServerResponse,
    McpToolResponse,
)
from hify.modules.mcp.application.commands.create_server import (
    CreateMcpServerCommand,
    CreateMcpServerHandler,
)
from hify.modules.mcp.application.commands.refresh_tools import (
    RefreshMcpToolsCommand,
    RefreshMcpToolsHandler,
)
from hify.modules.mcp.application.queries.get_server import (
    GetMcpServerForActorHandler,
    GetMcpServerForActorQuery,
    ListMcpServersForActorHandler,
)
from hify.modules.mcp.application.queries.list_tools import (
    ListMcpToolsForActorHandler,
    ListMcpToolsForActorQuery,
)
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_mcp_router(
    *,
    create_server_handler: CreateMcpServerHandler,
    get_server_handler: GetMcpServerForActorHandler,
    list_servers_handler: ListMcpServersForActorHandler,
    list_tools_handler: ListMcpToolsForActorHandler,
    refresh_tools_handler: RefreshMcpToolsHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/mcp", tags=["mcp"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("/servers", response_model=McpServerResponse, status_code=status.HTTP_201_CREATED)
    async def create_server(
        request: CreateMcpServerRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> McpServerResponse:
        try:
            server = await create_server_handler.handle(
                CreateMcpServerCommand(
                    actor=actor,
                    name=request.name,
                    description=request.description,
                    transport=request.transport,
                    endpoint_url=request.endpoint_url,
                )
            )
            return McpServerResponse.model_validate(server)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/servers", response_model=tuple[McpServerResponse, ...])
    async def list_servers(
        actor: ActorContext = Depends(get_current_actor),
    ) -> tuple[McpServerResponse, ...]:
        try:
            servers = await list_servers_handler.handle(actor=actor)
            return tuple(McpServerResponse.model_validate(server) for server in servers)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/servers/{server_id}", response_model=McpServerResponse)
    async def get_server(
        server_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> McpServerResponse:
        try:
            server = await get_server_handler.handle(
                GetMcpServerForActorQuery(actor=actor, server_id=server_id)
            )
            return McpServerResponse.model_validate(server)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/servers/{server_id}/tools", response_model=tuple[McpToolResponse, ...])
    async def list_tools(
        server_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> tuple[McpToolResponse, ...]:
        try:
            tools = await list_tools_handler.handle(
                ListMcpToolsForActorQuery(actor=actor, server_id=server_id)
            )
            return tuple(McpToolResponse.model_validate(tool) for tool in tools)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("/servers/{server_id}/refresh-tools", response_model=tuple[McpToolResponse, ...])
    async def refresh_tools(
        server_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> tuple[McpToolResponse, ...]:
        try:
            tools = await refresh_tools_handler.handle(
                RefreshMcpToolsCommand(actor=actor, server_id=server_id)
            )
            return tuple(McpToolResponse.model_validate(tool) for tool in tools)
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
