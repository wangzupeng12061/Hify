from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import FastAPI
from fastapi.testclient import TestClient

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.api.router import create_runs_router
from hify.modules.runs.api.router import _stream_run_execution
from hify.modules.runs.application.executor import ExecuteRunCommand
from hify.modules.runs.application.queries.list_run_events import ListRunEventsForActorQuery
from hify.modules.runs.contracts.dto import RunEventInfo, RunEventPage, RunInfo


RUN_ID = UUID("00000000-0000-7000-8000-000000000001")
TEAM_ID = UUID("00000000-0000-7000-8000-000000000002")
USER_ID = UUID("00000000-0000-7000-8000-000000000003")


class StaticAuthenticator:
    async def authenticate(self, request: Any) -> ActorContext:
        return ActorContext(
            user_id=USER_ID,
            team_id=TEAM_ID,
            membership_id=UUID("00000000-0000-7000-8000-000000000004"),
            role="member",
            permissions=("runs.execute", "runs.read"),
        )


class UnusedHandler:
    async def handle(self, command: Any) -> Any:
        raise AssertionError("handler should not be called")


class RecordingRunExecutor:
    def __init__(self, events: list[RunEventInfo]) -> None:
        self.events = events
        self.prepare_commands: list[ExecuteRunCommand] = []
        self.execute_commands: list[ExecuteRunCommand] = []

    async def prepare_execution(self, command: ExecuteRunCommand) -> RunInfo:
        self.prepare_commands.append(command)
        return _run_info("queued")

    async def execute(self, command: ExecuteRunCommand) -> RunInfo:
        self.execute_commands.append(command)
        self.events.extend(
            [
                _run_event(sequence_number=1, event_type="run.started"),
                _run_event(sequence_number=2, event_type="output.text_delta", payload={"text": "Hi"}),
                _run_event(sequence_number=3, event_type="run.succeeded"),
            ]
        )
        return _run_info("succeeded")


class RecordingListEventsHandler:
    def __init__(self, events: list[RunEventInfo]) -> None:
        self.events = events
        self.queries: list[ListRunEventsForActorQuery] = []

    async def handle(self, query: ListRunEventsForActorQuery) -> RunEventPage:
        self.queries.append(query)
        after_sequence_number = int(query.cursor) if query.cursor is not None else 0
        items = tuple(
            event
            for event in self.events
            if event.run_id == query.run_id and event.sequence_number > after_sequence_number
        )
        return RunEventPage(items=items[: query.limit], next_cursor=None, has_more=False)


class DisconnectingRequest:
    async def is_disconnected(self) -> bool:
        return True


class CancellationAwareRunExecutor:
    def __init__(self, events: list[RunEventInfo]) -> None:
        self.events = events
        self.cancelled = False

    async def execute(self, command: ExecuteRunCommand) -> RunInfo:
        assert command.cancellation is not None
        while not command.cancellation.is_cancelled():
            await asyncio.sleep(0)
        self.cancelled = True
        self.events.append(_run_event(sequence_number=1, event_type="run.cancelled"))
        return _run_info("cancelled")


def test_execute_stream_returns_run_events_as_sse() -> None:
    events: list[RunEventInfo] = []
    run_executor = RecordingRunExecutor(events)
    list_events_handler = RecordingListEventsHandler(events)
    app = FastAPI()
    app.include_router(
        create_runs_router(
            create_run_handler=UnusedHandler(),
            cancel_run_handler=UnusedHandler(),
            get_run_handler=UnusedHandler(),
            get_run_diagnostics_handler=UnusedHandler(),
            list_events_handler=list_events_handler,
            run_executor=run_executor,
            request_authenticator=StaticAuthenticator(),
        )
    )
    client = TestClient(app)

    with client.stream("POST", f"/runs/{RUN_ID}/execute-stream") as response:
        body = "".join(response.iter_text())

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: run.started" in body
    assert "event: output.text_delta" in body
    assert "event: run.succeeded" in body
    assert '"text":"Hi"' in body
    assert run_executor.prepare_commands[0].actor is not None
    assert run_executor.execute_commands[0].cancellation is not None
    assert list_events_handler.queries[0].actor.has_permission("runs.read")


def test_stream_disconnect_requests_executor_cancellation_before_force_cancel() -> None:
    async def run_stream() -> tuple[list[str], CancellationAwareRunExecutor]:
        events: list[RunEventInfo] = []
        run_executor = CancellationAwareRunExecutor(events)
        list_events_handler = RecordingListEventsHandler(events)
        actor = await StaticAuthenticator().authenticate(object())
        chunks: list[str] = []
        async for chunk in _stream_run_execution(
            request=DisconnectingRequest(),
            actor=actor,
            run_id=RUN_ID,
            run_executor=run_executor,
            list_events_handler=list_events_handler,
        ):
            chunks.append(chunk)
        return chunks, run_executor

    chunks, run_executor = asyncio.run(run_stream())

    assert chunks == []
    assert run_executor.cancelled


def _run_event(
    *,
    sequence_number: int,
    event_type: str,
    payload: dict[str, object] | None = None,
) -> RunEventInfo:
    return RunEventInfo(
        id=UUID(f"00000000-0000-7000-8000-{sequence_number:012d}"),
        team_id=TEAM_ID,
        run_id=RUN_ID,
        sequence_number=sequence_number,
        event_type=event_type,
        payload=payload or {"run_id": str(RUN_ID)},
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
    )


def _run_info(status: str) -> RunInfo:
    return RunInfo(
        id=RUN_ID,
        team_id=TEAM_ID,
        conversation_id=UUID("00000000-0000-7000-8000-000000000005"),
        agent_id=UUID("00000000-0000-7000-8000-000000000006"),
        agent_version_id=UUID("00000000-0000-7000-8000-000000000007"),
        status=status,
        step_count=0,
        event_count=0,
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
        updated_at=datetime(2026, 6, 22, tzinfo=UTC),
        started_at=None,
        completed_at=None,
        duration_ms=None,
        error_code=None,
        error_message=None,
    )
