from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.api.dependencies import RequestAuthenticator
from hify.modules.runs.api.schemas import CreateRunRequest, RunEventPageResponse, RunResponse
from hify.modules.runs.application.commands.cancel_run import CancelRunCommand, CancelRunHandler
from hify.modules.runs.application.commands.create_run import CreateRunCommand, CreateRunHandler
from hify.modules.runs.application.queries.get_run import GetRunForActorHandler, GetRunForActorQuery
from hify.modules.runs.application.queries.list_run_events import (
    ListRunEventsForActorHandler,
    ListRunEventsForActorQuery,
)
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError


def create_runs_router(
    *,
    create_run_handler: CreateRunHandler,
    cancel_run_handler: CancelRunHandler,
    get_run_handler: GetRunForActorHandler,
    list_events_handler: ListRunEventsForActorHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/runs", tags=["runs"])

    async def get_current_actor(request: Request) -> ActorContext:
        try:
            return await request_authenticator.authenticate(request)
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
    async def create_run(
        request: CreateRunRequest,
        actor: ActorContext = Depends(get_current_actor),
    ) -> RunResponse:
        try:
            command = CreateRunCommand(
                actor=actor,
                conversation_id=request.conversation_id,
                idempotency_key=request.idempotency_key,
            )
            run = await create_run_handler.handle(command)
            return RunResponse.model_validate(run)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/{run_id}", response_model=RunResponse)
    async def get_run(
        run_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> RunResponse:
        try:
            query = GetRunForActorQuery(actor=actor, run_id=run_id)
            run = await get_run_handler.handle(query)
            return RunResponse.model_validate(run)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.post("/{run_id}/cancel", response_model=RunResponse)
    async def cancel_run(
        run_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> RunResponse:
        try:
            command = CancelRunCommand(actor=actor, run_id=run_id)
            run = await cancel_run_handler.handle(command)
            return RunResponse.model_validate(run)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

    @router.get("/{run_id}/events", response_model=RunEventPageResponse)
    async def list_run_events(
        run_id: UUID,
        cursor: str | None = None,
        limit: int = Query(default=20, ge=1, le=100),
        actor: ActorContext = Depends(get_current_actor),
    ) -> RunEventPageResponse:
        try:
            query = ListRunEventsForActorQuery(
                actor=actor,
                run_id=run_id,
                cursor=cursor,
                limit=limit,
            )
            page = await list_events_handler.handle(query)
            return RunEventPageResponse.model_validate(page)
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
