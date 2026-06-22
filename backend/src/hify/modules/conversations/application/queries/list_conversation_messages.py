from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.conversations.application.authorization import require_read_conversations
from hify.modules.conversations.application.dto import conversation_message_info_from_domain
from hify.modules.conversations.application.ports import ConversationsUnitOfWorkFactory
from hify.modules.conversations.application.queries.get_conversation import (
    GetConversationHandler,
    GetConversationQuery,
)
from hify.modules.conversations.contracts.dto import ConversationInfo, ConversationMessagePage
from hify.modules.conversations.contracts.services import ConversationReader
from hify.modules.conversations.domain.errors import ConversationNotFoundError
from hify.modules.conversations.domain.value_objects import parse_message_cursor
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.pagination import PageRequest, build_page


@dataclass(frozen=True, slots=True)
class ListConversationMessagesQuery:
    team_id: UUID
    conversation_id: UUID
    cursor: str | None
    limit: int


@dataclass(frozen=True, slots=True)
class ListConversationMessagesForActorQuery:
    actor: ActorContext
    conversation_id: UUID
    cursor: str | None
    limit: int


class ListConversationMessagesHandler:
    def __init__(self, unit_of_work_factory: ConversationsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: ListConversationMessagesQuery) -> ConversationMessagePage:
        page_request = PageRequest(limit=query.limit, cursor=query.cursor)
        after_sequence_number = parse_message_cursor(query.cursor)

        async with self._unit_of_work_factory() as unit_of_work:
            conversation = await unit_of_work.conversations.get_by_id(query.conversation_id)
            if conversation is None or conversation.team_id != query.team_id:
                raise ConversationNotFoundError("conversation was not found")
            messages = await unit_of_work.messages.list_by_conversation(
                conversation_id=query.conversation_id,
                after_sequence_number=after_sequence_number,
                limit=page_request.limit_plus_one,
            )

        next_cursor = (
            str(messages[page_request.limit - 1].sequence_number)
            if len(messages) > page_request.limit
            else None
        )
        page = build_page(
            [conversation_message_info_from_domain(message) for message in messages],
            page_request,
            next_cursor,
        )
        return ConversationMessagePage(
            items=page.items,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )


class ListConversationMessagesForActorHandler:
    def __init__(self, list_messages_handler: ListConversationMessagesHandler) -> None:
        self._list_messages_handler = list_messages_handler

    async def handle(
        self,
        query: ListConversationMessagesForActorQuery,
    ) -> ConversationMessagePage:
        require_read_conversations(query.actor)
        return await self._list_messages_handler.handle(
            ListConversationMessagesQuery(
                team_id=query.actor.team_id,
                conversation_id=query.conversation_id,
                cursor=query.cursor,
                limit=query.limit,
            )
        )


class ConversationReaderService(ConversationReader):
    def __init__(
        self,
        get_conversation_handler: GetConversationHandler,
        list_messages_handler: ListConversationMessagesHandler,
    ) -> None:
        self._get_conversation_handler = get_conversation_handler
        self._list_messages_handler = list_messages_handler

    async def get_conversation(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
    ) -> ConversationInfo:
        return await self._get_conversation_handler.handle(
            GetConversationQuery(team_id=team_id, conversation_id=conversation_id)
        )

    async def list_messages(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> ConversationMessagePage:
        return await self._list_messages_handler.handle(
            ListConversationMessagesQuery(
                team_id=team_id,
                conversation_id=conversation_id,
                cursor=cursor,
                limit=limit,
            )
        )
