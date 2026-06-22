from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from collections.abc import AsyncIterator

from hify.modules.agents.contracts.dto import AgentVersionInfo
from hify.modules.conversations.contracts.dto import (
    ConversationInfo,
    ConversationMessageInfo,
    ConversationMessagePage,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.contracts.dto import RetrievedChunk
from hify.modules.providers.contracts.dto import (
    CallContext,
    DoneChunk,
    ModelChunk,
    ModelRequest,
    TextDeltaChunk,
    ToolCallDeltaChunk,
    UsageChunk,
    ModelUsage,
)
from hify.modules.providers.contracts.errors import (
    ProviderStreamInterruptedError,
    ProviderUnavailableError,
)
from hify.modules.runs.contracts.dto import RunInfo
from hify.modules.runs.application.commands.cancel_run import CancelRunCommand, CancelRunHandler
from hify.modules.runs.application.commands.create_run import CreateRunCommand, CreateRunHandler
from hify.modules.runs.application.executor import ExecuteRunCommand, RunExecutor
from hify.modules.runs.application.queries.get_run import (
    GetRunForActorHandler,
    GetRunForActorQuery,
    GetRunHandler,
)
from hify.modules.runs.application.queries.list_run_events import (
    ListRunEventsHandler,
    ListRunEventsQuery,
    RunReaderService,
)
from hify.modules.runs.domain.entities import AgentRun, RunEvent, RunStep
from hify.modules.runs.domain.errors import RunPermissionDeniedError
from hify.modules.runs.domain.value_objects import RunEventType
from hify.modules.tools.contracts.dto import ToolExecutionRequest, ToolExecutionResult
from hify.modules.tools.contracts.errors import ToolExecutionHttpError
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeConversationReader:
    def __init__(
        self,
        conversation: ConversationInfo,
        messages: tuple[ConversationMessageInfo, ...] = (),
    ) -> None:
        self.conversation = conversation
        self.messages = messages

    async def get_conversation(self, *, team_id: UUID, conversation_id: UUID) -> ConversationInfo:
        assert team_id == self.conversation.team_id
        assert conversation_id == self.conversation.id
        return self.conversation

    async def list_messages(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> ConversationMessagePage:
        assert team_id == self.conversation.team_id
        assert conversation_id == self.conversation.id
        assert cursor is None
        assert limit > 0
        return ConversationMessagePage(items=self.messages, next_cursor=None, has_more=False)


class FakeAgentCatalog:
    def __init__(self, agent_version: AgentVersionInfo) -> None:
        self.agent_version = agent_version

    async def get_latest_published_version(
        self,
        *,
        team_id: UUID,
        agent_id: UUID,
    ) -> AgentVersionInfo:
        assert team_id == self.agent_version.team_id
        assert agent_id == self.agent_version.agent_id
        return self.agent_version

    async def get_agent_version(
        self,
        *,
        team_id: UUID,
        agent_version_id: UUID,
    ) -> AgentVersionInfo:
        assert team_id == self.agent_version.team_id
        assert agent_version_id == self.agent_version.id
        return self.agent_version


class FakeRunRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, AgentRun] = {}

    async def add(self, run: AgentRun) -> None:
        self.items[run.id] = run

    async def save(self, run: AgentRun) -> None:
        self.items[run.id] = run

    async def get_by_id(self, run_id: UUID) -> AgentRun | None:
        return self.items.get(run_id)

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
    ) -> AgentRun | None:
        for run in self.items.values():
            if (
                run.team_id == team_id
                and run.conversation_id == conversation_id
                and run.idempotency_key == idempotency_key
            ):
                return run
        return None


class FakeStepRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, RunStep] = {}

    async def add(self, step: RunStep) -> None:
        self.items[step.id] = step

    async def save(self, step: RunStep) -> None:
        self.items[step.id] = step

    async def get_by_id(self, step_id: UUID) -> RunStep | None:
        return self.items.get(step_id)

    async def list_by_run(self, *, run_id: UUID) -> tuple[RunStep, ...]:
        steps = [step for step in self.items.values() if step.run_id == run_id]
        return tuple(sorted(steps, key=lambda step: step.sequence_number))


class FakeEventRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, RunEvent] = {}

    async def add(self, event: RunEvent) -> None:
        self.items[event.id] = event

    async def list_by_run(
        self,
        *,
        run_id: UUID,
        after_sequence_number: int | None,
        limit: int,
    ) -> tuple[RunEvent, ...]:
        events = [
            event
            for event in self.items.values()
            if event.run_id == run_id
            and (
                after_sequence_number is None
                or event.sequence_number > after_sequence_number
            )
        ]
        events.sort(key=lambda event: event.sequence_number)
        return tuple(events[:limit])


class FakeRunsUnitOfWork:
    def __init__(self) -> None:
        self.runs = FakeRunRepository()
        self.steps = FakeStepRepository()
        self.events = FakeEventRepository()
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


def actor_with_run_permissions() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="member",
        permissions=("runs.execute", "runs.read"),
    )


def conversation_for_actor(actor: ActorContext) -> ConversationInfo:
    return ConversationInfo(
        id=UUID("00000000-0000-7000-8000-000000000004"),
        team_id=actor.team_id,
        agent_id=UUID("00000000-0000-7000-8000-000000000005"),
        title=None,
        status="active",
        message_count=1,
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
        updated_at=datetime(2026, 6, 22, tzinfo=UTC),
    )


def agent_version_for_conversation(conversation: ConversationInfo) -> AgentVersionInfo:
    return AgentVersionInfo(
        id=UUID("00000000-0000-7000-8000-000000000006"),
        team_id=conversation.team_id,
        agent_id=conversation.agent_id,
        version_number=1,
        name="Support Bot",
        description=None,
        system_prompt="You are helpful.",
        knowledge_base_ids=(),
        workflow_id=None,
        workflow_version_id=None,
        workflow_version_number=None,
        workflow_name=None,
        workflow_definition=None,
        provider_model_id=UUID("00000000-0000-7000-8000-000000000007"),
        provider_type="openai",
        provider_name="OpenAI",
        model_name="gpt-4.1",
        model_display_name="GPT 4.1",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=False,
        supports_structured_output=True,
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
    )


def agent_version_with_workflow(conversation: ConversationInfo) -> AgentVersionInfo:
    return AgentVersionInfo(
        id=UUID("00000000-0000-7000-8000-000000000006"),
        team_id=conversation.team_id,
        agent_id=conversation.agent_id,
        version_number=1,
        name="Support Bot",
        description=None,
        system_prompt="You are helpful.",
        knowledge_base_ids=(),
        workflow_id=UUID("00000000-0000-7000-8000-000000000010"),
        workflow_version_id=UUID("00000000-0000-7000-8000-000000000011"),
        workflow_version_number=2,
        workflow_name="Support Flow",
        workflow_definition={
            "nodes": [
                {"id": "start", "kind": "start", "config": {}},
                {"id": "end", "kind": "end", "config": {}},
            ],
            "edges": [{"source_node_id": "start", "target_node_id": "end"}],
        },
        provider_model_id=UUID("00000000-0000-7000-8000-000000000007"),
        provider_type="openai",
        provider_name="OpenAI",
        model_name="gpt-4.1",
        model_display_name="GPT 4.1",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=False,
        supports_structured_output=True,
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
    )


class RecordingModelGateway:
    def __init__(self, chunks: tuple[ModelChunk, ...], error: Exception | None = None) -> None:
        self.chunks = chunks
        self.error = error
        self.requests: list[ModelRequest] = []
        self.contexts: list[CallContext] = []

    def stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        self.requests.append(request)
        self.contexts.append(context)
        return self._stream()

    async def _stream(self) -> AsyncIterator[ModelChunk]:
        for chunk in self.chunks:
            yield chunk
        if self.error is not None:
            raise self.error


class SequencedModelGateway:
    def __init__(self, chunks_by_request: tuple[tuple[ModelChunk, ...], ...]) -> None:
        self.chunks_by_request = chunks_by_request
        self.requests: list[ModelRequest] = []
        self.contexts: list[CallContext] = []

    def stream(
        self,
        request: ModelRequest,
        context: CallContext,
    ) -> AsyncIterator[ModelChunk]:
        self.requests.append(request)
        self.contexts.append(context)
        return self._stream(self.chunks_by_request[len(self.requests) - 1])

    async def _stream(self, chunks: tuple[ModelChunk, ...]) -> AsyncIterator[ModelChunk]:
        for chunk in chunks:
            yield chunk


class RecordingToolExecutor:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.requests: list[ToolExecutionRequest] = []

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return ToolExecutionResult(
            tool_call_id=request.tool_call_id,
            content="tool result",
            metadata={"ok": True},
        )


class RecordingKnowledgeRetriever:
    def __init__(self, chunks: tuple[RetrievedChunk, ...] = ()) -> None:
        self.chunks = chunks
        self.requests: list[tuple[UUID, UUID, tuple[UUID, ...], str, int, float | None]] = []

    async def retrieve(
        self,
        *,
        team_id: UUID,
        user_id: UUID,
        knowledge_base_ids: tuple[UUID, ...],
        query: str,
        limit: int,
        deadline: float | None = None,
    ) -> tuple[RetrievedChunk, ...]:
        self.requests.append((team_id, user_id, knowledge_base_ids, query, limit, deadline))
        return self.chunks


@pytest.mark.asyncio
async def test_create_run_uses_conversation_and_latest_agent_version() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    handler = CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        FixedClock(),
    )

    run = await handler.handle(
        CreateRunCommand(
            actor=actor,
            conversation_id=conversation.id,
            idempotency_key="run-1",
        )
    )

    assert run.conversation_id == conversation.id
    assert run.agent_id == conversation.agent_id
    assert run.agent_version_id == UUID("00000000-0000-7000-8000-000000000006")
    assert run.event_count == 1
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_create_run_records_workflow_version_payload_when_bound() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    agent_version = agent_version_with_workflow(conversation)
    handler = CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version),
        FixedClock(),
    )

    await handler.handle(
        CreateRunCommand(
            actor=actor,
            conversation_id=conversation.id,
            idempotency_key="run-1",
        )
    )

    event = next(iter(unit_of_work.events.items.values()))
    assert event.payload["workflow_id"] == str(agent_version.workflow_id)
    assert event.payload["workflow_version_id"] == str(agent_version.workflow_version_id)
    assert event.payload["workflow_version_number"] == agent_version.workflow_version_number
    assert event.payload["workflow_name"] == "Support Flow"


@pytest.mark.asyncio
async def test_create_run_is_idempotent() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    handler = CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        FixedClock(),
    )
    command = CreateRunCommand(
        actor=actor,
        conversation_id=conversation.id,
        idempotency_key="run-1",
    )

    first = await handler.handle(command)
    second = await handler.handle(command)

    assert first == second
    assert len(unit_of_work.runs.items) == 1
    assert len(unit_of_work.events.items) == 1


@pytest.mark.asyncio
async def test_create_run_requires_execute_permission() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=("runs.read",),
    )
    conversation = conversation_for_actor(actor)
    handler = CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        FixedClock(),
    )

    with pytest.raises(RunPermissionDeniedError):
        await handler.handle(
            CreateRunCommand(
                actor=actor,
                conversation_id=conversation.id,
                idempotency_key="run-1",
            )
        )


@pytest.mark.asyncio
async def test_cancel_run_updates_status_and_writes_event() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    run = await _create_run(unit_of_work, actor)
    handler = CancelRunHandler(lambda: unit_of_work, FixedClock())

    cancelled = await handler.handle(CancelRunCommand(actor=actor, run_id=run.id))

    assert cancelled.status == "cancelled"
    assert cancelled.event_count == 2
    assert len(unit_of_work.events.items) == 2


@pytest.mark.asyncio
async def test_run_reader_returns_run_and_events() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    run = await _create_run(unit_of_work, actor)
    get_run_handler = GetRunHandler(lambda: unit_of_work)
    reader = RunReaderService(get_run_handler, ListRunEventsHandler(lambda: unit_of_work))

    fetched = await reader.get_run(team_id=actor.team_id, run_id=run.id)
    events = await reader.list_events(team_id=actor.team_id, run_id=run.id, cursor=None, limit=20)

    assert fetched == run
    assert len(events.items) == 1
    assert events.items[0].event_type == "run.created"


@pytest.mark.asyncio
async def test_list_events_for_actor_requires_read_permission() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="member",
        permissions=("runs.execute",),
    )
    run = await _create_run(unit_of_work, actor_with_run_permissions())

    with pytest.raises(RunPermissionDeniedError):
        await GetRunForActorHandler(GetRunHandler(lambda: unit_of_work)).handle(
            query=GetRunForActorQuery(actor=actor, run_id=run.id)
        )


@pytest.mark.asyncio
async def test_event_pagination_uses_cursor() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    run = await _create_run(unit_of_work, actor)
    domain_run = await unit_of_work.runs.get_by_id(run.id)
    assert domain_run is not None
    event = domain_run.create_event(
        event_type=RunEventType.DIAGNOSTIC,
        payload={"message": "queued"},
        now=FixedClock().now(),
    )
    await unit_of_work.runs.save(domain_run)
    await unit_of_work.events.add(event)

    page = await ListRunEventsHandler(lambda: unit_of_work).handle(
        ListRunEventsQuery(
            team_id=actor.team_id,
            run_id=run.id,
            cursor=None,
            limit=1,
        )
    )
    next_page = await ListRunEventsHandler(lambda: unit_of_work).handle(
        ListRunEventsQuery(
            team_id=actor.team_id,
            run_id=run.id,
            cursor=page.next_cursor,
            limit=1,
        )
    )

    assert page.has_more
    assert page.next_cursor == "1"
    assert next_page.items[0].sequence_number == 2


@pytest.mark.asyncio
async def test_run_executor_streams_model_chunks_into_run_events() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    message = ConversationMessageInfo(
        id=UUID("00000000-0000-7000-8000-000000000008"),
        team_id=actor.team_id,
        conversation_id=conversation.id,
        sequence_number=1,
        role="user",
        content="Hello",
        status="created",
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
    )
    run = await _create_run(unit_of_work, actor)
    gateway = RecordingModelGateway(
        (
            TextDeltaChunk(chunk_type="text_delta", text="Hi"),
            UsageChunk(chunk_type="usage", usage=ModelUsage(input_tokens=1, output_tokens=1)),
            DoneChunk(chunk_type="done", finish_reason="stop"),
        )
    )
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation, (message,)),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))
    events = await unit_of_work.events.list_by_run(
        run_id=run.id,
        after_sequence_number=None,
        limit=20,
    )
    steps = await unit_of_work.steps.list_by_run(run_id=run.id)

    assert result.status == "succeeded"
    assert gateway.requests[0].messages[0].content == "Hello"
    assert gateway.requests[0].system_prompt == "You are helpful."
    assert steps[0].status.value == "succeeded"
    assert [event.event_type.value for event in events] == [
        "run.created",
        "run.started",
        "step.started",
        "output.text_delta",
        "diagnostic",
        "diagnostic",
        "step.succeeded",
        "run.succeeded",
    ]


@pytest.mark.asyncio
async def test_run_executor_records_workflow_snapshot_without_executing_workflow() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    agent_version = agent_version_with_workflow(conversation)
    gateway = RecordingModelGateway((DoneChunk(chunk_type="done", finish_reason="stop"),))
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version),
        gateway,
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))
    events = await unit_of_work.events.list_by_run(
        run_id=run.id,
        after_sequence_number=None,
        limit=20,
    )
    workflow_events = [
        event
        for event in events
        if event.payload.get("chunk_type") == "workflow_snapshot"
    ]

    assert result.status == "succeeded"
    assert len(gateway.requests) == 1
    assert len(workflow_events) == 1
    assert workflow_events[0].payload["workflow_version_id"] == str(
        agent_version.workflow_version_id
    )
    assert workflow_events[0].payload["workflow_definition"] == agent_version.workflow_definition


@pytest.mark.asyncio
async def test_run_executor_marks_run_failed_on_provider_error() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        RecordingModelGateway((), ProviderUnavailableError("model unavailable")),
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "failed"
    assert result.error_code == "PROVIDER_UNAVAILABLE_ERROR"


@pytest.mark.asyncio
async def test_run_executor_marks_run_interrupted_after_stream_interruption() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        RecordingModelGateway(
            (TextDeltaChunk(chunk_type="text_delta", text="partial"),),
            ProviderStreamInterruptedError("stream interrupted"),
        ),
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "interrupted"
    assert result.error_code == "PROVIDER_STREAM_INTERRUPTED_ERROR"


@pytest.mark.asyncio
async def test_run_executor_retrieves_knowledge_and_injects_context() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    message = ConversationMessageInfo(
        id=UUID("00000000-0000-7000-8000-000000000008"),
        team_id=actor.team_id,
        conversation_id=conversation.id,
        sequence_number=1,
        role="user",
        content="How do I restart the API?",
        status="created",
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
    )
    run = await _create_run(unit_of_work, actor)
    gateway = RecordingModelGateway((DoneChunk(chunk_type="done", finish_reason="stop"),))
    knowledge_base_id = UUID("00000000-0000-7000-8000-000000000090")
    agent_version = AgentVersionInfo(
        id=UUID("00000000-0000-7000-8000-000000000006"),
        team_id=conversation.team_id,
        agent_id=conversation.agent_id,
        version_number=1,
        name="Support Bot",
        description=None,
        system_prompt="You are helpful.",
        knowledge_base_ids=(knowledge_base_id,),
        workflow_id=None,
        workflow_version_id=None,
        workflow_version_number=None,
        workflow_name=None,
        workflow_definition=None,
        provider_model_id=UUID("00000000-0000-7000-8000-000000000007"),
        provider_type="openai",
        provider_name="OpenAI",
        model_name="gpt-4.1",
        model_display_name="GPT 4.1",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=False,
        supports_structured_output=True,
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
    )
    retriever = RecordingKnowledgeRetriever(
        (
            RetrievedChunk(
                chunk_id=UUID("00000000-0000-7000-8000-000000000091"),
                team_id=actor.team_id,
                knowledge_base_id=knowledge_base_id,
                document_id=UUID("00000000-0000-7000-8000-000000000092"),
                position=0,
                content="Restart the API by rolling the api deployment.",
                score=0.87,
            ),
        )
    )
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation, (message,)),
        FakeAgentCatalog(agent_version),
        gateway,
        RecordingToolExecutor(),
        retriever,
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))
    events = await unit_of_work.events.list_by_run(
        run_id=run.id,
        after_sequence_number=None,
        limit=30,
    )
    steps = await unit_of_work.steps.list_by_run(run_id=run.id)

    assert result.status == "succeeded"
    assert retriever.requests[0][2] == (knowledge_base_id,)
    assert retriever.requests[0][3] == "How do I restart the API?"
    assert "Restart the API by rolling the api deployment." in (gateway.requests[0].system_prompt or "")
    assert [step.step_type.value for step in steps] == ["retrieval", "llm_call"]
    assert "retrieval_result" in [event.payload.get("chunk_type") for event in events]


@pytest.mark.asyncio
async def test_run_executor_executes_tool_calls_and_continues_model_loop() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    tool_id = UUID("00000000-0000-7000-8000-000000000011")
    tool_call_id = UUID("00000000-0000-7000-8000-000000000012")
    gateway = SequencedModelGateway(
        (
            (
                ToolCallDeltaChunk(
                    chunk_type="tool_call_delta",
                    tool_call_id=str(tool_call_id),
                    name=str(tool_id),
                    arguments_delta='{"email":"owner@example.com"}',
                ),
                DoneChunk(chunk_type="done", finish_reason="tool_calls"),
            ),
            (
                TextDeltaChunk(chunk_type="text_delta", text="Done"),
                DoneChunk(chunk_type="done", finish_reason="stop"),
            ),
        )
    )
    tool_executor = RecordingToolExecutor()
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        tool_executor,
        RecordingKnowledgeRetriever(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))
    events = await unit_of_work.events.list_by_run(
        run_id=run.id,
        after_sequence_number=None,
        limit=30,
    )
    steps = await unit_of_work.steps.list_by_run(run_id=run.id)

    assert result.status == "succeeded"
    assert tool_executor.requests[0] == ToolExecutionRequest(
        team_id=actor.team_id,
        tool_id=tool_id,
        tool_call_id=tool_call_id,
        arguments={"email": "owner@example.com"},
    )
    assert gateway.requests[1].messages[-1].role == "tool"
    assert gateway.requests[1].messages[-1].content == "tool result"
    assert [step.step_type.value for step in steps] == ["llm_call", "tool_call", "llm_call"]
    assert "tool_result" in [event.payload.get("chunk_type") for event in events]


@pytest.mark.asyncio
async def test_run_executor_marks_run_failed_when_tool_fails() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    gateway = SequencedModelGateway(
        (
            (
                ToolCallDeltaChunk(
                    chunk_type="tool_call_delta",
                    tool_call_id="00000000-0000-7000-8000-000000000012",
                    name="00000000-0000-7000-8000-000000000011",
                    arguments_delta="{}",
                ),
                DoneChunk(chunk_type="done", finish_reason="tool_calls"),
            ),
        )
    )
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(ToolExecutionHttpError("tool failed")),
        RecordingKnowledgeRetriever(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "failed"
    assert result.error_code == "TOOL_EXECUTION_HTTP_ERROR"


@pytest.mark.asyncio
async def test_run_executor_enforces_max_tool_iterations() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    tool_id = UUID("00000000-0000-7000-8000-000000000011")
    gateway = SequencedModelGateway(
        (
            (
                ToolCallDeltaChunk(
                    chunk_type="tool_call_delta",
                    tool_call_id="00000000-0000-7000-8000-000000000012",
                    name=str(tool_id),
                    arguments_delta="{}",
                ),
                DoneChunk(chunk_type="done", finish_reason="tool_calls"),
            ),
            (
                ToolCallDeltaChunk(
                    chunk_type="tool_call_delta",
                    tool_call_id="00000000-0000-7000-8000-000000000013",
                    name=str(tool_id),
                    arguments_delta="{}",
                ),
                DoneChunk(chunk_type="done", finish_reason="tool_calls"),
            ),
        )
    )
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        FixedClock(),
        max_tool_iterations=1,
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "failed"
    assert result.error_code == "RUN_TOOL_ITERATION_LIMIT_EXCEEDED"


async def _create_run(unit_of_work: FakeRunsUnitOfWork, actor: ActorContext) -> RunInfo:
    conversation = conversation_for_actor(actor)
    return await CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        FixedClock(),
    ).handle(
        CreateRunCommand(
            actor=actor,
            conversation_id=conversation.id,
            idempotency_key="run-1",
        )
    )
