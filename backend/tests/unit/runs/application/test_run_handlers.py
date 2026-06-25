from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from collections.abc import AsyncIterator

from decimal import Decimal

from hify.modules.agents.contracts.dto import AgentVersionInfo
from hify.modules.conversations.contracts.dto import (
    ConversationInfo,
    ConversationMessageInfo,
    ConversationMessagePage,
)
from hify.modules.conversations.contracts.errors import ConversationContractError
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
from hify.modules.runs.application.queries.get_run_diagnostics import (
    GetRunDiagnosticsHandler,
    GetRunDiagnosticsQuery,
)
from hify.modules.runs.application.queries.list_run_events import (
    ListRunEventsHandler,
    ListRunEventsQuery,
    RunReaderService,
)
from hify.modules.runs.domain.entities import AgentRun, RunEvent, RunStep
from hify.modules.runs.domain.errors import RunPermissionDeniedError
from hify.modules.runs.domain.value_objects import RunEventType, RunStepType
from hify.modules.tools.contracts.dto import ToolExecutionRequest, ToolExecutionResult, ToolInfo
from hify.modules.tools.contracts.errors import ToolExecutionHttpError
from hify.modules.usage.contracts.dto import UsageQuotaStatusInfo, UsageRecordInfo, UsageSummaryInfo
from hify.modules.usage.contracts.errors import UsageContractError, UsageQuotaExceededError
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


class RecordingConversationWriter:
    def __init__(self, error: ConversationContractError | None = None) -> None:
        self.error = error
        self.requests: list[tuple[UUID, UUID, str, UUID, UUID]] = []

    async def append_assistant_message(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        content: str,
        source_run_id: UUID,
        created_by: UUID,
    ) -> ConversationMessageInfo:
        self.requests.append((team_id, conversation_id, content, source_run_id, created_by))
        if self.error is not None:
            raise self.error
        return ConversationMessageInfo(
            id=UUID("00000000-0000-7000-8000-000000000099"),
            team_id=team_id,
            conversation_id=conversation_id,
            sequence_number=2,
            role="assistant",
            content=content,
            status="created",
            created_at=datetime(2026, 6, 22, tzinfo=UTC),
        )


class RecordingUsageRecorder:
    def __init__(self, error: UsageContractError | None = None) -> None:
        self.error = error
        self.requests: list[tuple[UUID, UUID, UUID, int, int, str]] = []

    async def record_model_usage(
        self,
        *,
        team_id: UUID,
        user_id: UUID,
        run_id: UUID,
        agent_id: UUID,
        agent_version_id: UUID,
        provider_model_id: UUID,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_amount: Decimal,
        idempotency_key: str,
        occurred_at: datetime,
    ) -> UsageRecordInfo:
        self.requests.append(
            (team_id, user_id, run_id, input_tokens, output_tokens, idempotency_key)
        )
        if self.error is not None:
            raise self.error
        return UsageRecordInfo(
            id=UUID("00000000-0000-7000-8000-000000000098"),
            team_id=team_id,
            user_id=user_id,
            run_id=run_id,
            agent_id=agent_id,
            agent_version_id=agent_version_id,
            provider_model_id=provider_model_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_amount=cost_amount,
            idempotency_key=idempotency_key,
            occurred_at=occurred_at,
            created_at=datetime(2026, 6, 22, tzinfo=UTC),
        )


class RecordingUsageQuotaChecker:
    def __init__(self, error: UsageQuotaExceededError | None = None) -> None:
        self.error = error
        self.requests: list[tuple[UUID, datetime]] = []

    async def ensure_team_quota_available(
        self,
        *,
        team_id: UUID,
        at: datetime,
    ) -> UsageQuotaStatusInfo:
        self.requests.append((team_id, at))
        if self.error is not None:
            raise self.error
        return UsageQuotaStatusInfo(
            team_id=team_id,
            monthly_token_limit=None,
            used_tokens=0,
            remaining_tokens=None,
            is_exceeded=False,
            period_start=datetime(2026, 6, 1, tzinfo=UTC),
            period_end=datetime(2026, 7, 1, tzinfo=UTC),
        )


class FakeUsageReader:
    async def get_team_summary(self, *, team_id: UUID) -> UsageSummaryInfo:
        return UsageSummaryInfo(
            team_id=team_id,
            run_id=None,
            input_tokens=0,
            output_tokens=0,
            total_tokens=0,
            cost_amount=Decimal("0"),
        )

    async def get_run_summary(self, *, team_id: UUID, run_id: UUID) -> UsageSummaryInfo:
        return UsageSummaryInfo(
            team_id=team_id,
            run_id=run_id,
            input_tokens=11,
            output_tokens=7,
            total_tokens=18,
            cost_amount=Decimal("0.12345678"),
        )


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
    model_id = UUID("00000000-0000-7000-8000-000000000007")
    tool_id = UUID("00000000-0000-7000-8000-000000000012")
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
                {
                    "id": "llm",
                    "kind": "llm",
                    "config": {"provider_model_id": str(model_id)},
                },
                {
                    "id": "tool",
                    "kind": "tool",
                    "config": {
                        "tool_id": str(tool_id),
                        "arguments": {"query": "status"},
                    },
                },
                {"id": "end", "kind": "end", "config": {}},
            ],
            "edges": [
                {"source_node_id": "start", "target_node_id": "llm"},
                {"source_node_id": "llm", "target_node_id": "tool"},
                {"source_node_id": "tool", "target_node_id": "end"},
            ],
        },
        provider_model_id=model_id,
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


def agent_version_with_unsupported_workflow(conversation: ConversationInfo) -> AgentVersionInfo:
    agent_version = agent_version_with_workflow(conversation)
    return AgentVersionInfo(
        id=agent_version.id,
        team_id=agent_version.team_id,
        agent_id=agent_version.agent_id,
        version_number=agent_version.version_number,
        name=agent_version.name,
        description=agent_version.description,
        system_prompt=agent_version.system_prompt,
        knowledge_base_ids=agent_version.knowledge_base_ids,
        workflow_id=agent_version.workflow_id,
        workflow_version_id=agent_version.workflow_version_id,
        workflow_version_number=agent_version.workflow_version_number,
        workflow_name=agent_version.workflow_name,
        workflow_definition={
            "nodes": [
                {"id": "start", "kind": "start", "config": {}},
                {"id": "left", "kind": "llm", "config": {"provider_model_id": str(agent_version.provider_model_id)}},
                {"id": "right", "kind": "llm", "config": {"provider_model_id": str(agent_version.provider_model_id)}},
                {"id": "end", "kind": "end", "config": {}},
            ],
            "edges": [
                {"source_node_id": "start", "target_node_id": "left"},
                {"source_node_id": "start", "target_node_id": "right"},
                {"source_node_id": "left", "target_node_id": "end"},
                {"source_node_id": "right", "target_node_id": "end"},
            ],
        },
        provider_model_id=agent_version.provider_model_id,
        provider_type=agent_version.provider_type,
        provider_name=agent_version.provider_name,
        model_name=agent_version.model_name,
        model_display_name=agent_version.model_display_name,
        context_window_tokens=agent_version.context_window_tokens,
        supports_tools=agent_version.supports_tools,
        supports_vision=agent_version.supports_vision,
        supports_structured_output=agent_version.supports_structured_output,
        created_at=agent_version.created_at,
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
    def __init__(
        self,
        error: Exception | None = None,
        *,
        content: str = "tool result",
        metadata: dict[str, object] | None = None,
    ) -> None:
        self.error = error
        self.content = content
        self.metadata = metadata or {"ok": True}
        self.requests: list[ToolExecutionRequest] = []

    async def execute_tool(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        self.requests.append(request)
        if self.error is not None:
            raise self.error
        return ToolExecutionResult(
            tool_call_id=request.tool_call_id,
            content=self.content,
            metadata=self.metadata,
        )


class FakeToolCatalog:
    def __init__(self, tools: tuple[ToolInfo, ...] = ()) -> None:
        self.tools = tools
        self.requests: list[UUID] = []

    async def get_tool(self, *, team_id: UUID, tool_id: UUID) -> ToolInfo:
        for tool in self.tools:
            if tool.team_id == team_id and tool.id == tool_id:
                return tool
        raise AssertionError("unexpected tool lookup")

    async def list_tools(self, *, team_id: UUID) -> tuple[ToolInfo, ...]:
        self.requests.append(team_id)
        return tuple(tool for tool in self.tools if tool.team_id == team_id)


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
    quota_checker = RecordingUsageQuotaChecker()
    handler = CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        quota_checker,
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
    assert quota_checker.requests == [(actor.team_id, FixedClock().now())]
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
        RecordingUsageQuotaChecker(),
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
    quota_checker = RecordingUsageQuotaChecker()
    handler = CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        quota_checker,
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
    assert len(quota_checker.requests) == 1


@pytest.mark.asyncio
async def test_create_run_rejects_when_team_quota_exceeded() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    quota_checker = RecordingUsageQuotaChecker(
        UsageQuotaExceededError("team monthly token quota has been exceeded")
    )
    handler = CreateRunHandler(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        quota_checker,
        FixedClock(),
    )

    with pytest.raises(UsageQuotaExceededError):
        await handler.handle(
            CreateRunCommand(
                actor=actor,
                conversation_id=conversation.id,
                idempotency_key="run-1",
            )
        )

    assert quota_checker.requests == [(actor.team_id, FixedClock().now())]
    assert unit_of_work.runs.items == {}


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
        RecordingUsageQuotaChecker(),
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
async def test_run_diagnostics_returns_run_summary_and_steps() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    run = await _create_run(unit_of_work, actor)
    domain_run = await unit_of_work.runs.get_by_id(run.id)
    assert domain_run is not None
    step = domain_run.create_step(
        step_type=RunStepType.LLM_CALL,
        name="Model call",
        now=FixedClock().now(),
    )
    step.mark_failed(
        error_code="PROVIDER_UNAVAILABLE_ERROR",
        error_message="provider unavailable",
        now=FixedClock().now(),
    )
    domain_run.mark_failed(
        error_code="PROVIDER_UNAVAILABLE_ERROR",
        error_message="provider unavailable",
        now=FixedClock().now(),
    )
    await unit_of_work.runs.save(domain_run)
    await unit_of_work.steps.add(step)

    diagnostics = await GetRunDiagnosticsHandler(lambda: unit_of_work, FakeUsageReader()).handle(
        GetRunDiagnosticsQuery(actor=actor, run_id=run.id)
    )

    assert diagnostics.status == "failed"
    assert diagnostics.error_code == "PROVIDER_UNAVAILABLE_ERROR"
    assert diagnostics.steps[0].step_type == "llm_call"
    assert diagnostics.steps[0].error_code == "PROVIDER_UNAVAILABLE_ERROR"
    assert diagnostics.steps[0].duration_ms == 0
    assert diagnostics.usage_total_tokens == 18
    assert diagnostics.usage_cost_amount == Decimal("0.12345678")


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
    conversation_writer = RecordingConversationWriter()
    usage_recorder = RecordingUsageRecorder()
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation, (message,)),
        conversation_writer,
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        usage_recorder,
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
    assert conversation_writer.requests == [
        (actor.team_id, conversation.id, "Hi", run.id, actor.user_id)
    ]
    assert usage_recorder.requests == [
        (
            actor.team_id,
            actor.user_id,
            run.id,
            1,
            1,
            f"run:{run.id}:step:{steps[0].id}:usage:1",
        )
    ]
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
async def test_run_executor_injects_active_tool_definitions_for_tool_capable_model() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    tool_id = UUID("00000000-0000-7000-8000-000000000011")
    tool_catalog = FakeToolCatalog(
        (
            ToolInfo(
                id=tool_id,
                team_id=actor.team_id,
                name="Web Search",
                description="Search current public web information.",
                tool_kind="builtin",
                status="active",
                input_schema={
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                },
                builtin_name="web.search",
                endpoint_url=None,
                http_method=None,
                http_headers={},
                mcp_server_id=None,
                mcp_tool_id=None,
                mcp_tool_name=None,
                created_at=FixedClock().now(),
                updated_at=FixedClock().now(),
            ),
            ToolInfo(
                id=UUID("00000000-0000-7000-8000-000000000012"),
                team_id=actor.team_id,
                name="Disabled Search",
                description=None,
                tool_kind="builtin",
                status="disabled",
                input_schema={"type": "object"},
                builtin_name="web.search",
                endpoint_url=None,
                http_method=None,
                http_headers={},
                mcp_server_id=None,
                mcp_tool_id=None,
                mcp_tool_name=None,
                created_at=FixedClock().now(),
                updated_at=FixedClock().now(),
            ),
        )
    )
    gateway = RecordingModelGateway((DoneChunk(chunk_type="done", finish_reason="stop"),))
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        RecordingConversationWriter(),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
        FixedClock(),
        tool_catalog=tool_catalog,
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "succeeded"
    assert tool_catalog.requests == [actor.team_id]
    assert gateway.requests[0].tools == (
        {
            "type": "function",
            "function": {
                "name": str(tool_id),
                "description": (
                    "Use the Hify tool named 'Web Search'. Target: web.search. "
                    "Search current public web information."
                ),
                "parameters": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                },
            },
        },
    )


@pytest.mark.asyncio
async def test_run_executor_records_diagnostic_when_conversation_write_fails() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    gateway = RecordingModelGateway(
        (
            TextDeltaChunk(chunk_type="text_delta", text="Hi"),
            DoneChunk(chunk_type="done", finish_reason="stop"),
        )
    )
    conversation_writer = RecordingConversationWriter(
        ConversationContractError("conversation write failed")
    )
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        conversation_writer,
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))
    events = await unit_of_work.events.list_by_run(
        run_id=run.id,
        after_sequence_number=None,
        limit=20,
    )

    assert result.status == "succeeded"
    assert conversation_writer.requests == [
        (actor.team_id, conversation.id, "Hi", run.id, actor.user_id)
    ]
    diagnostic_event = events[-1]
    assert diagnostic_event.event_type == RunEventType.DIAGNOSTIC
    assert diagnostic_event.payload == {
        "chunk_type": "assistant_output_write_failed",
        "error_code": "CONVERSATION_CONTRACT_ERROR",
        "message": "conversation write failed",
    }


@pytest.mark.asyncio
async def test_run_executor_executes_linear_workflow_runtime() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    agent_version = agent_version_with_workflow(conversation)
    gateway = RecordingModelGateway(
        (
            TextDeltaChunk(chunk_type="text_delta", text="Workflow response"),
            DoneChunk(chunk_type="done", finish_reason="stop"),
        )
    )
    tool_executor = RecordingToolExecutor()
    conversation_writer = RecordingConversationWriter()
    usage_recorder = RecordingUsageRecorder()
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        conversation_writer,
        FakeAgentCatalog(agent_version),
        gateway,
        tool_executor,
        RecordingKnowledgeRetriever(),
        usage_recorder,
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
    steps = await unit_of_work.steps.list_by_run(run_id=run.id)

    assert result.status == "succeeded"
    assert conversation_writer.requests == [
        (actor.team_id, conversation.id, "Workflow response", run.id, actor.user_id)
    ]
    assert usage_recorder.requests == []
    assert len(gateway.requests) == 1
    assert gateway.requests[0].model_id == agent_version.provider_model_id
    assert gateway.requests[0].system_prompt == "You are helpful."
    assert len(tool_executor.requests) == 1
    assert tool_executor.requests[0].arguments == {"query": "status"}
    assert len(workflow_events) == 1
    assert workflow_events[0].payload["workflow_version_id"] == str(
        agent_version.workflow_version_id
    )
    assert workflow_events[0].payload["workflow_definition"] == agent_version.workflow_definition
    assert [step.step_type.value for step in steps] == [
        "system",
        "llm_call",
        "tool_call",
        "system",
    ]


@pytest.mark.asyncio
async def test_run_executor_rejects_unsupported_workflow_definition() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        RecordingConversationWriter(),
        FakeAgentCatalog(agent_version_with_unsupported_workflow(conversation)),
        RecordingModelGateway(()),
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "failed"
    assert result.error_code == "WORKFLOW_RUNTIME_UNSUPPORTED_DEFINITION"


@pytest.mark.asyncio
async def test_run_executor_marks_workflow_run_failed_when_tool_node_fails() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    conversation_writer = RecordingConversationWriter()
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        conversation_writer,
        FakeAgentCatalog(agent_version_with_workflow(conversation)),
        RecordingModelGateway((DoneChunk(chunk_type="done", finish_reason="stop"),)),
        RecordingToolExecutor(ToolExecutionHttpError("tool failed")),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "failed"
    assert result.error_code == "TOOL_EXECUTION_HTTP_ERROR"
    assert conversation_writer.requests == []


@pytest.mark.asyncio
async def test_run_executor_marks_run_failed_on_provider_error() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    conversation_writer = RecordingConversationWriter()
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        conversation_writer,
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        RecordingModelGateway((), ProviderUnavailableError("model unavailable")),
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
        FixedClock(),
    )

    result = await executor.execute(ExecuteRunCommand(run_id=run.id))

    assert result.status == "failed"
    assert result.error_code == "PROVIDER_UNAVAILABLE_ERROR"
    assert conversation_writer.requests == []


@pytest.mark.asyncio
async def test_run_executor_marks_run_interrupted_after_stream_interruption() -> None:
    unit_of_work = FakeRunsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = conversation_for_actor(actor)
    run = await _create_run(unit_of_work, actor)
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        RecordingConversationWriter(),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        RecordingModelGateway(
            (TextDeltaChunk(chunk_type="text_delta", text="partial"),),
            ProviderStreamInterruptedError("stream interrupted"),
        ),
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
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
        RecordingConversationWriter(),
        FakeAgentCatalog(agent_version),
        gateway,
        RecordingToolExecutor(),
        retriever,
        RecordingUsageRecorder(),
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
    assert "activity.started" in [event.event_type.value for event in events]
    assert "activity.completed" in [event.event_type.value for event in events]
    assert "source.discovered" in [event.event_type.value for event in events]


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
    tool_executor = RecordingToolExecutor(
        content=(
            '{"results":[{"title":"Ceph releases","url":"https://docs.ceph.com/releases",'
            '"snippet":"Release notes"}]}'
        ),
        metadata={"provider": "duckduckgo"},
    )
    conversation_writer = RecordingConversationWriter()
    usage_recorder = RecordingUsageRecorder()
    executor = RunExecutor(
        lambda: unit_of_work,
        FakeConversationReader(conversation),
        conversation_writer,
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        tool_executor,
        RecordingKnowledgeRetriever(),
        usage_recorder,
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
    assert conversation_writer.requests == [
        (actor.team_id, conversation.id, "Done", run.id, actor.user_id)
    ]
    assert usage_recorder.requests == []
    assert tool_executor.requests[0] == ToolExecutionRequest(
        team_id=actor.team_id,
        tool_id=tool_id,
        tool_call_id=tool_call_id,
        arguments={"email": "owner@example.com"},
    )
    assert gateway.requests[1].messages[-1].role == "tool"
    assert gateway.requests[1].messages[-1].content == (
        '{"results":[{"title":"Ceph releases","url":"https://docs.ceph.com/releases",'
        '"snippet":"Release notes"}]}'
    )
    assert [step.step_type.value for step in steps] == ["llm_call", "tool_call", "llm_call"]
    assert "tool_result" in [event.payload.get("chunk_type") for event in events]
    source_events = [event for event in events if event.event_type.value == "source.discovered"]
    assert source_events[0].payload["title"] == "Ceph releases"
    assert source_events[0].payload["url"] == "https://docs.ceph.com/releases"


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
        RecordingConversationWriter(),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(ToolExecutionHttpError("tool failed")),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
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
        RecordingConversationWriter(),
        FakeAgentCatalog(agent_version_for_conversation(conversation)),
        gateway,
        RecordingToolExecutor(),
        RecordingKnowledgeRetriever(),
        RecordingUsageRecorder(),
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
        RecordingUsageQuotaChecker(),
        FixedClock(),
    ).handle(
        CreateRunCommand(
            actor=actor,
            conversation_id=conversation.id,
            idempotency_key="run-1",
        )
    )
