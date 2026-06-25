from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import suppress
from time import monotonic
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.api.dependencies import RequestAuthenticator
from hify.modules.runs.api.schemas import (
    CreateRunRequest,
    RunDiagnosticsResponse,
    RunEventPageResponse,
    RunEventResponse,
    RunResponse,
)
from hify.modules.runs.application.commands.cancel_run import CancelRunCommand, CancelRunHandler
from hify.modules.runs.application.commands.create_run import CreateRunCommand, CreateRunHandler
from hify.modules.runs.application.executor import (
    ExecuteRunCommand,
    RunCancellationToken,
    RunExecutor,
)
from hify.modules.runs.application.queries.get_run import GetRunForActorHandler, GetRunForActorQuery
from hify.modules.runs.application.queries.get_run_diagnostics import (
    GetRunDiagnosticsHandler,
    GetRunDiagnosticsQuery,
)
from hify.modules.runs.application.queries.list_run_events import (
    ListRunEventsForActorHandler,
    ListRunEventsForActorQuery,
)
from hify.modules.runs.contracts.dto import RunEventInfo, RunInfo
from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, PermissionDeniedError

SSE_EVENT_PAGE_LIMIT = 50
SSE_POLL_INTERVAL_SECONDS = 0.1
SSE_HEARTBEAT_SECONDS = 15.0
SSE_DISCONNECT_SHUTDOWN_GRACE_SECONDS = 5.0
TERMINAL_RUN_EVENT_TYPES = frozenset(
    {
        "run.succeeded",
        "run.failed",
        "run.cancelled",
        "run.interrupted",
    }
)


def create_runs_router(
    *,
    create_run_handler: CreateRunHandler,
    cancel_run_handler: CancelRunHandler,
    get_run_handler: GetRunForActorHandler,
    get_run_diagnostics_handler: GetRunDiagnosticsHandler,
    list_events_handler: ListRunEventsForActorHandler,
    run_executor: RunExecutor,
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

    @router.get("/{run_id}/diagnostics", response_model=RunDiagnosticsResponse)
    async def get_run_diagnostics(
        run_id: UUID,
        actor: ActorContext = Depends(get_current_actor),
    ) -> RunDiagnosticsResponse:
        try:
            query = GetRunDiagnosticsQuery(actor=actor, run_id=run_id)
            diagnostics = await get_run_diagnostics_handler.handle(query)
            return RunDiagnosticsResponse.model_validate(diagnostics)
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

    @router.post("/{run_id}/execute-stream")
    async def execute_run_stream(
        run_id: UUID,
        request: Request,
        actor: ActorContext = Depends(get_current_actor),
    ) -> StreamingResponse:
        try:
            command = ExecuteRunCommand(run_id=run_id, actor=actor)
            await run_executor.prepare_execution(command)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except HifyError as exc:
            raise _to_http_error(exc) from exc

        return StreamingResponse(
            _stream_run_execution(
                request=request,
                actor=actor,
                run_id=run_id,
                run_executor=run_executor,
                list_events_handler=list_events_handler,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

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


async def _stream_run_execution(
    *,
    request: Request,
    actor: ActorContext,
    run_id: UUID,
    run_executor: RunExecutor,
    list_events_handler: ListRunEventsForActorHandler,
) -> AsyncIterator[str]:
    cancellation = RunCancellationToken()
    task = asyncio.create_task(
        run_executor.execute(
            ExecuteRunCommand(run_id=run_id, actor=actor, cancellation=cancellation)
        )
    )
    cursor: str | None = None
    terminal_event_seen = False
    last_sent_at = monotonic()

    try:
        while True:
            if await request.is_disconnected():
                await _request_execution_shutdown(task, cancellation)
                break

            page = await list_events_handler.handle(
                ListRunEventsForActorQuery(
                    actor=actor,
                    run_id=run_id,
                    cursor=cursor,
                    limit=SSE_EVENT_PAGE_LIMIT,
                )
            )
            for event in page.items:
                cursor = str(event.sequence_number)
                terminal_event_seen = event.event_type in TERMINAL_RUN_EVENT_TYPES
                yield _encode_sse_event(event)
                last_sent_at = monotonic()

            if terminal_event_seen:
                await _observe_execution_task(task)
                break
            if page.has_more:
                continue
            if task.done():
                await _observe_execution_task(task)
                break

            if monotonic() - last_sent_at >= SSE_HEARTBEAT_SECONDS:
                yield ": heartbeat\n\n"
                last_sent_at = monotonic()

            await asyncio.sleep(SSE_POLL_INTERVAL_SECONDS)
    finally:
        if not task.done():
            await _request_execution_shutdown(task, cancellation)
        elif terminal_event_seen:
            await _observe_execution_task(task)


async def _observe_execution_task(task: asyncio.Task[RunInfo]) -> None:
    await task


async def _request_execution_shutdown(
    task: asyncio.Task[RunInfo],
    cancellation: RunCancellationToken,
) -> None:
    cancellation.cancel()
    if task.done():
        await _observe_execution_task(task)
        return
    try:
        await asyncio.wait_for(
            asyncio.shield(task),
            timeout=SSE_DISCONNECT_SHUTDOWN_GRACE_SECONDS,
        )
    except TimeoutError:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


def _encode_sse_event(event: RunEventInfo) -> str:
    data = RunEventResponse.model_validate(event).model_dump_json()
    return f"id: {event.sequence_number}\nevent: {event.event_type}\ndata: {data}\n\n"


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
