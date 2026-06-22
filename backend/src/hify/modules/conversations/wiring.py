from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.conversations.api.router import create_conversations_router
from hify.modules.conversations.application.commands.append_conversation_message import (
    AppendConversationMessageHandler,
)
from hify.modules.conversations.application.commands.create_conversation import (
    CreateConversationHandler,
)
from hify.modules.conversations.application.commands.submit_message_feedback import (
    SubmitMessageFeedbackHandler,
)
from hify.modules.conversations.application.queries.get_conversation import (
    GetConversationHandler,
)
from hify.modules.conversations.application.queries.list_conversation_messages import (
    ConversationReaderService,
    ListConversationMessagesForActorHandler,
    ListConversationMessagesHandler,
)
from hify.modules.conversations.contracts.services import ConversationReader
from hify.modules.conversations.infrastructure.database.uow import SqlAlchemyConversationsUnitOfWork
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class ConversationsModule:
    router: APIRouter
    conversation_reader: ConversationReader


def create_conversations_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    agent_catalog: AgentCatalog,
    clock: Clock | None = None,
) -> ConversationsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyConversationsUnitOfWork:
        return SqlAlchemyConversationsUnitOfWork(session_factory)

    create_conversation_handler = CreateConversationHandler(
        unit_of_work_factory,
        agent_catalog,
        module_clock,
    )
    append_message_handler = AppendConversationMessageHandler(unit_of_work_factory, module_clock)
    submit_feedback_handler = SubmitMessageFeedbackHandler(unit_of_work_factory, module_clock)
    get_conversation_handler = GetConversationHandler(unit_of_work_factory)
    list_messages_handler = ListConversationMessagesHandler(unit_of_work_factory)
    list_messages_for_actor_handler = ListConversationMessagesForActorHandler(list_messages_handler)
    conversation_reader = ConversationReaderService(
        get_conversation_handler,
        list_messages_handler,
    )
    router = create_conversations_router(
        create_conversation_handler=create_conversation_handler,
        append_message_handler=append_message_handler,
        list_messages_handler=list_messages_for_actor_handler,
        submit_feedback_handler=submit_feedback_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return ConversationsModule(router=router, conversation_reader=conversation_reader)
