from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from hify.modules.identity.api.dependencies import DevelopmentTeamIdHeader, DevelopmentUserIdHeader
from hify.modules.identity.api.schemas import (
    ActorContextResponse,
    AddTeamMemberRequest,
    CreateTeamRequest,
    CreateUserRequest,
    MembershipResponse,
    TeamResponse,
    UserResponse,
)
from hify.modules.identity.application.commands.add_team_member import (
    AddTeamMemberCommand,
    AddTeamMemberHandler,
)
from hify.modules.identity.application.commands.create_team import CreateTeamCommand, CreateTeamHandler
from hify.modules.identity.application.commands.create_user import CreateUserCommand, CreateUserHandler
from hify.modules.identity.application.queries.get_actor_context import (
    GetActorContextHandler,
    GetActorContextQuery,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_identity_router(
    *,
    create_user_handler: CreateUserHandler,
    create_team_handler: CreateTeamHandler,
    add_team_member_handler: AddTeamMemberHandler,
    get_actor_context_handler: GetActorContextHandler,
    allow_development_header_auth: bool = False,
) -> APIRouter:
    router = APIRouter(prefix="/identity", tags=["identity"])

    async def get_current_actor(
        header_user_id: DevelopmentUserIdHeader = None,
        header_team_id: DevelopmentTeamIdHeader = None,
    ) -> ActorContext:
        if not allow_development_header_auth:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "AUTHENTICATION_NOT_CONFIGURED",
                    "message": "authentication is not configured for this API",
                },
            )
        if header_user_id is None or header_team_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "AUTHENTICATION_REQUIRED",
                    "message": "development header authentication requires user and team headers",
                },
            )
        try:
            query = GetActorContextQuery(user_id=header_user_id, team_id=header_team_id)
            return await get_actor_context_handler.handle(query)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post(
        "/users",
        response_model=UserResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_user(request: CreateUserRequest) -> UserResponse:
        try:
            command = CreateUserCommand(
                email=str(request.email),
                display_name=request.display_name,
            )
            user = await create_user_handler.handle(command)
            return UserResponse.model_validate(user)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post(
        "/teams",
        response_model=TeamResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_team(request: CreateTeamRequest) -> TeamResponse:
        try:
            command = CreateTeamCommand(name=request.name, owner_user_id=request.owner_user_id)
            team = await create_team_handler.handle(command)
            return TeamResponse.model_validate(team)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/me", response_model=ActorContextResponse)
    async def get_me(
        actor: ActorContext = Depends(get_current_actor),
    ) -> ActorContextResponse:
        return ActorContextResponse(
            user_id=actor.user_id,
            team_id=actor.team_id,
            membership_id=actor.membership_id,
            role=actor.role,
            permissions=actor.permissions,
        )

    @router.post(
        "/teams/{team_id}/members",
        response_model=MembershipResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def add_team_member(
        team_id: UUID,
        request: AddTeamMemberRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> MembershipResponse:
        try:
            command = AddTeamMemberCommand(
                actor=actor,
                team_id=team_id,
                user_id=request.user_id,
                role=request.role,
            )
            membership = await add_team_member_handler.handle(command)
            return MembershipResponse.model_validate(membership)
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
