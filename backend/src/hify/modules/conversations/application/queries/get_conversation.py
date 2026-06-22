from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.conversations.application.authorization import require_read_conversations
from hify.modules.conversations.application.dto import conversation_info_from_domain
from hify.modules.conversations.application.ports import ConversationsUnitOfWorkFactory
from hify.modules.conversations.contracts.dto import ConversationInfo
from hify.modules.conversations.domain.errors import ConversationNotFoundError
from hify.modules.identity.contracts.dto import ActorContext


@dataclass(frozen=True, slots=True)
class GetConversationQuery:
    team_id: UUID
    conversation_id: UUID


@dataclass(frozen=True, slots=True)
class GetConversationForActorQuery:
    actor: ActorContext
    conversation_id: UUID


class GetConversationHandler:
    def __init__(self, unit_of_work_factory: ConversationsUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetConversationQuery) -> ConversationInfo:
        async with self._unit_of_work_factory() as unit_of_work:
            conversation = await unit_of_work.conversations.get_by_id(query.conversation_id)
        if conversation is None or conversation.team_id != query.team_id:
            raise ConversationNotFoundError("conversation was not found")
        return conversation_info_from_domain(conversation)


class GetConversationForActorHandler:
    def __init__(self, get_conversation_handler: GetConversationHandler) -> None:
        self._get_conversation_handler = get_conversation_handler

    async def handle(self, query: GetConversationForActorQuery) -> ConversationInfo:
        require_read_conversations(query.actor)
        return await self._get_conversation_handler.handle(
            GetConversationQuery(
                team_id=query.actor.team_id,
                conversation_id=query.conversation_id,
            )
        )
