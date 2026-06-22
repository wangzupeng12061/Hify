from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from hify.modules.agents.api.dependencies import RequestAuthenticator
from hify.modules.agents.api.schemas import AgentResponse, AgentVersionResponse, CreateAgentRequest
from hify.modules.agents.application.commands.create_agent import CreateAgentCommand, CreateAgentHandler
from hify.modules.agents.application.commands.publish_agent import (
    PublishAgentCommand,
    PublishAgentHandler,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_agents_router(
    *,
    create_agent_handler: CreateAgentHandler,
    publish_agent_handler: PublishAgentHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/agents", tags=["agents"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
    async def create_agent(
        request: CreateAgentRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> AgentResponse:
        try:
            command = CreateAgentCommand(
                actor=actor,
                name=request.name,
                description=request.description,
                system_prompt=request.system_prompt,
                provider_model_id=request.provider_model_id,
            )
            agent = await create_agent_handler.handle(command)
            return AgentResponse.model_validate(agent)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post(
        "/{agent_id}/publish",
        response_model=AgentVersionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def publish_agent(
        agent_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> AgentVersionResponse:
        try:
            command = PublishAgentCommand(actor=actor, agent_id=agent_id)
            agent_version = await publish_agent_handler.handle(command)
            return AgentVersionResponse.model_validate(agent_version)
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
