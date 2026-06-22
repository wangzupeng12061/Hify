from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.agents.contracts.dto import AgentVersionInfo
from hify.modules.conversations.application.commands.append_assistant_message import (
    AppendAssistantMessageCommand,
    AppendAssistantMessageHandler,
)
from hify.modules.conversations.application.commands.append_conversation_message import (
    AppendConversationMessageCommand,
    AppendConversationMessageHandler,
)
from hify.modules.conversations.application.commands.create_conversation import (
    CreateConversationCommand,
    CreateConversationHandler,
)
from hify.modules.conversations.application.commands.submit_message_feedback import (
    SubmitMessageFeedbackCommand,
    SubmitMessageFeedbackHandler,
)
from hify.modules.conversations.application.queries.get_conversation import GetConversationHandler
from hify.modules.conversations.application.queries.list_conversation_messages import (
    ConversationReaderService,
    ListConversationMessagesHandler,
    ListConversationMessagesQuery,
)
from hify.modules.conversations.domain.entities import (
    Conversation,
    ConversationMessage,
    MessageFeedback,
)
from hify.modules.conversations.domain.errors import ConversationPermissionDeniedError
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeAgentCatalog:
    def __init__(self, agent_version: AgentVersionInfo) -> None:
        self.agent_version = agent_version
        self.requested_agent_id: UUID | None = None

    async def get_latest_published_version(
        self,
        *,
        team_id: UUID,
        agent_id: UUID,
    ) -> AgentVersionInfo:
        assert team_id == self.agent_version.team_id
        self.requested_agent_id = agent_id
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


class FakeConversationRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Conversation] = {}

    async def add(self, conversation: Conversation) -> None:
        self.items[conversation.id] = conversation

    async def save(self, conversation: Conversation) -> None:
        self.items[conversation.id] = conversation

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        return self.items.get(conversation_id)


class FakeMessageRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, ConversationMessage] = {}

    async def add(self, message: ConversationMessage) -> None:
        self.items[message.id] = message

    async def get_by_id(self, message_id: UUID) -> ConversationMessage | None:
        return self.items.get(message_id)

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
    ) -> ConversationMessage | None:
        for message in self.items.values():
            if (
                message.team_id == team_id
                and message.conversation_id == conversation_id
                and message.idempotency_key == idempotency_key
            ):
                return message
        return None

    async def list_by_conversation(
        self,
        *,
        conversation_id: UUID,
        after_sequence_number: int | None,
        limit: int,
    ) -> tuple[ConversationMessage, ...]:
        messages = [
            message
            for message in self.items.values()
            if message.conversation_id == conversation_id
            and (
                after_sequence_number is None
                or message.sequence_number > after_sequence_number
            )
        ]
        messages.sort(key=lambda message: message.sequence_number)
        return tuple(messages[:limit])


class FakeFeedbackRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, MessageFeedback] = {}

    async def add(self, feedback: MessageFeedback) -> None:
        self.items[feedback.id] = feedback

    async def save(self, feedback: MessageFeedback) -> None:
        self.items[feedback.id] = feedback

    async def get_by_message_and_user(
        self,
        *,
        message_id: UUID,
        created_by: UUID,
    ) -> MessageFeedback | None:
        for feedback in self.items.values():
            if feedback.message_id == message_id and feedback.created_by == created_by:
                return feedback
        return None


class FakeConversationsUnitOfWork:
    def __init__(self) -> None:
        self.conversations = FakeConversationRepository()
        self.messages = FakeMessageRepository()
        self.feedback = FakeFeedbackRepository()
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


def published_agent_version(team_id: UUID) -> AgentVersionInfo:
    return AgentVersionInfo(
        id=UUID("00000000-0000-7000-8000-000000000004"),
        team_id=team_id,
        agent_id=UUID("00000000-0000-7000-8000-000000000005"),
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
        provider_model_id=UUID("00000000-0000-7000-8000-000000000006"),
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
async def test_create_conversation_validates_published_agent() -> None:
    unit_of_work = FakeConversationsUnitOfWork()
    actor = actor_with_run_permissions()
    agent_catalog = FakeAgentCatalog(published_agent_version(actor.team_id))
    handler = CreateConversationHandler(lambda: unit_of_work, agent_catalog, FixedClock())

    conversation = await handler.handle(
        CreateConversationCommand(
            actor=actor,
            agent_id=agent_catalog.agent_version.agent_id,
            title="Support",
        )
    )

    assert conversation.agent_id == agent_catalog.agent_version.agent_id
    assert agent_catalog.requested_agent_id == agent_catalog.agent_version.agent_id
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_create_conversation_requires_execute_permission() -> None:
    unit_of_work = FakeConversationsUnitOfWork()
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=("runs.read",),
    )
    handler = CreateConversationHandler(
        lambda: unit_of_work,
        FakeAgentCatalog(published_agent_version(actor.team_id)),
        FixedClock(),
    )

    with pytest.raises(ConversationPermissionDeniedError):
        await handler.handle(
            CreateConversationCommand(
                actor=actor,
                agent_id=UUID("00000000-0000-7000-8000-000000000005"),
                title=None,
            )
        )


@pytest.mark.asyncio
async def test_append_message_is_idempotent_and_messages_page_uses_cursor() -> None:
    unit_of_work = FakeConversationsUnitOfWork()
    actor = actor_with_run_permissions()
    create_handler = CreateConversationHandler(
        lambda: unit_of_work,
        FakeAgentCatalog(published_agent_version(actor.team_id)),
        FixedClock(),
    )
    conversation = await create_handler.handle(
        CreateConversationCommand(
            actor=actor,
            agent_id=UUID("00000000-0000-7000-8000-000000000005"),
            title=None,
        )
    )
    append_handler = AppendConversationMessageHandler(lambda: unit_of_work, FixedClock())

    first = await append_handler.handle(
        AppendConversationMessageCommand(
            actor=actor,
            conversation_id=conversation.id,
            content="hello",
            idempotency_key="message-1",
        )
    )
    second = await append_handler.handle(
        AppendConversationMessageCommand(
            actor=actor,
            conversation_id=conversation.id,
            content="ignored duplicate body",
            idempotency_key="message-1",
        )
    )

    assert first == second
    assert len(unit_of_work.messages.items) == 1

    page = await ListConversationMessagesHandler(lambda: unit_of_work).handle(
        ListConversationMessagesQuery(
            team_id=actor.team_id,
            conversation_id=conversation.id,
            cursor=None,
            limit=1,
        )
    )
    assert page.items == (first,)
    assert not page.has_more


@pytest.mark.asyncio
async def test_append_assistant_message_is_idempotent_by_source_run() -> None:
    unit_of_work = FakeConversationsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = await CreateConversationHandler(
        lambda: unit_of_work,
        FakeAgentCatalog(published_agent_version(actor.team_id)),
        FixedClock(),
    ).handle(
        CreateConversationCommand(
            actor=actor,
            agent_id=UUID("00000000-0000-7000-8000-000000000005"),
            title=None,
        )
    )
    handler = AppendAssistantMessageHandler(lambda: unit_of_work, FixedClock())
    source_run_id = UUID("00000000-0000-7000-8000-000000000009")

    first = await handler.handle(
        AppendAssistantMessageCommand(
            team_id=actor.team_id,
            conversation_id=conversation.id,
            content="assistant output",
            source_run_id=source_run_id,
            created_by=actor.user_id,
        )
    )
    second = await handler.handle(
        AppendAssistantMessageCommand(
            team_id=actor.team_id,
            conversation_id=conversation.id,
            content="ignored duplicate output",
            source_run_id=source_run_id,
            created_by=actor.user_id,
        )
    )

    assert first == second
    assert first.role == "assistant"
    assert first.content == "assistant output"
    assert len(unit_of_work.messages.items) == 1
    assert unit_of_work.conversations.items[conversation.id].message_count == 1


@pytest.mark.asyncio
async def test_submit_feedback_updates_existing_feedback() -> None:
    unit_of_work = FakeConversationsUnitOfWork()
    actor = actor_with_run_permissions()
    create_handler = CreateConversationHandler(
        lambda: unit_of_work,
        FakeAgentCatalog(published_agent_version(actor.team_id)),
        FixedClock(),
    )
    conversation = await create_handler.handle(
        CreateConversationCommand(
            actor=actor,
            agent_id=UUID("00000000-0000-7000-8000-000000000005"),
            title=None,
        )
    )
    message = await AppendConversationMessageHandler(lambda: unit_of_work, FixedClock()).handle(
        AppendConversationMessageCommand(
            actor=actor,
            conversation_id=conversation.id,
            content="hello",
            idempotency_key="message-1",
        )
    )
    handler = SubmitMessageFeedbackHandler(lambda: unit_of_work, FixedClock())

    created = await handler.handle(
        SubmitMessageFeedbackCommand(
            actor=actor,
            conversation_id=conversation.id,
            message_id=message.id,
            rating="positive",
            comment="good",
        )
    )
    updated = await handler.handle(
        SubmitMessageFeedbackCommand(
            actor=actor,
            conversation_id=conversation.id,
            message_id=message.id,
            rating="negative",
            comment="bad",
        )
    )

    assert created.id == updated.id
    assert updated.rating == "negative"
    assert len(unit_of_work.feedback.items) == 1


@pytest.mark.asyncio
async def test_conversation_reader_returns_conversation_and_messages() -> None:
    unit_of_work = FakeConversationsUnitOfWork()
    actor = actor_with_run_permissions()
    conversation = await CreateConversationHandler(
        lambda: unit_of_work,
        FakeAgentCatalog(published_agent_version(actor.team_id)),
        FixedClock(),
    ).handle(
        CreateConversationCommand(
            actor=actor,
            agent_id=UUID("00000000-0000-7000-8000-000000000005"),
            title="Support",
        )
    )
    await AppendConversationMessageHandler(lambda: unit_of_work, FixedClock()).handle(
        AppendConversationMessageCommand(
            actor=actor,
            conversation_id=conversation.id,
            content="hello",
            idempotency_key="message-1",
        )
    )
    list_messages_handler = ListConversationMessagesHandler(lambda: unit_of_work)
    reader = ConversationReaderService(
        get_conversation_handler=GetConversationHandler(lambda: unit_of_work),
        list_messages_handler=list_messages_handler,
    )

    fetched = await reader.get_conversation(
        team_id=actor.team_id,
        conversation_id=conversation.id,
    )
    messages = await reader.list_messages(
        team_id=actor.team_id,
        conversation_id=conversation.id,
        cursor=None,
        limit=20,
    )

    assert fetched.id == conversation.id
    assert fetched.message_count == 1
    assert len(messages.items) == 1
