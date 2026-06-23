from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.conversations.application.authorization import require_read_conversations
from hify.modules.conversations.application.dto import conversation_info_from_domain
from hify.modules.conversations.application.ports import ConversationsUnitOfWorkFactory
from hify.modules.conversations.contracts.dto import ConversationPage
from hify.modules.conversations.domain.value_objects import (
    format_conversation_cursor,
    parse_conversation_cursor,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.pagination import PageRequest, build_page


@dataclass(frozen=True, slots=True)
class ListConversationsQuery:
    team_id: UUID
    cursor: str | None
    limit: int


@dataclass(frozen=True, slots=True)
class ListConversationsForActorQuery:
    actor: ActorContext
    cursor: str | None
    limit: int


class ListConversationsHandler:
    def __init__(self, unit_of_work_factory: ConversationsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: ListConversationsQuery) -> ConversationPage:
        page_request = PageRequest(limit=query.limit, cursor=query.cursor)
        before = parse_conversation_cursor(query.cursor)

        async with self._unit_of_work_factory() as unit_of_work:
            conversations = await unit_of_work.conversations.list_by_team(
                team_id=query.team_id,
                before=before,
                limit=page_request.limit_plus_one,
            )

        next_cursor = (
            format_conversation_cursor(
                conversations[page_request.limit - 1].created_at,
                conversations[page_request.limit - 1].id,
            )
            if len(conversations) > page_request.limit
            else None
        )
        page = build_page(
            [conversation_info_from_domain(conversation) for conversation in conversations],
            page_request,
            next_cursor,
        )
        return ConversationPage(
            items=page.items,
            next_cursor=page.next_cursor,
            has_more=page.has_more,
        )


class ListConversationsForActorHandler:
    def __init__(self, list_conversations_handler: ListConversationsHandler) -> None:
        self._list_conversations_handler = list_conversations_handler

    async def handle(self, query: ListConversationsForActorQuery) -> ConversationPage:
        require_read_conversations(query.actor)
        return await self._list_conversations_handler.handle(
            ListConversationsQuery(
                team_id=query.actor.team_id,
                cursor=query.cursor,
                limit=query.limit,
            )
        )
