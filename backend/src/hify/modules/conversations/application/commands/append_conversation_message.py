from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.conversations.application.authorization import require_execute_conversations
from hify.modules.conversations.application.dto import conversation_message_info_from_domain
from hify.modules.conversations.application.ports import ConversationsUnitOfWorkFactory
from hify.modules.conversations.contracts.dto import ConversationMessageInfo
from hify.modules.conversations.domain.errors import ConversationNotFoundError
from hify.modules.conversations.domain.value_objects import MessageRole, normalize_idempotency_key
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class AppendConversationMessageCommand:
    actor: ActorContext
    conversation_id: UUID
    content: str
    idempotency_key: str


class AppendConversationMessageHandler:
    def __init__(
        self,
        unit_of_work_factory: ConversationsUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(
        self,
        command: AppendConversationMessageCommand,
    ) -> ConversationMessageInfo:
        require_execute_conversations(command.actor)
        idempotency_key = normalize_idempotency_key(command.idempotency_key)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            conversation = await unit_of_work.conversations.get_by_id(command.conversation_id)
            if conversation is None or conversation.team_id != command.actor.team_id:
                raise ConversationNotFoundError("conversation was not found")

            existing_message = await unit_of_work.messages.get_by_idempotency_key(
                team_id=command.actor.team_id,
                conversation_id=command.conversation_id,
                idempotency_key=idempotency_key,
            )
            if existing_message is not None:
                return conversation_message_info_from_domain(existing_message)

            message = conversation.append_message(
                role=MessageRole.USER,
                content=command.content,
                created_by=command.actor.user_id,
                idempotency_key=idempotency_key,
                now=now,
            )
            await unit_of_work.conversations.save(conversation)
            await unit_of_work.messages.add(message)
            await unit_of_work.commit()
        return conversation_message_info_from_domain(message)
