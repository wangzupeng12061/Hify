from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.agents.contracts.dto import AgentVersionInfo
from hify.modules.conversations.contracts.dto import ConversationInfo, ConversationMessagePage
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.contracts.dto import RunInfo
from hify.modules.runs.application.commands.cancel_run import CancelRunCommand, CancelRunHandler
from hify.modules.runs.application.commands.create_run import CreateRunCommand, CreateRunHandler
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
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeConversationReader:
    def __init__(self, conversation: ConversationInfo) -> None:
        self.conversation = conversation

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
        return ConversationMessagePage(items=(), next_cursor=None, has_more=False)


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
