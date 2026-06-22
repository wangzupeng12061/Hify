from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.conversations.application.dto import conversation_message_info_from_domain
from hify.modules.conversations.application.ports import ConversationsUnitOfWorkFactory
from hify.modules.conversations.contracts.dto import ConversationMessageInfo
from hify.modules.conversations.contracts.services import ConversationWriter
from hify.modules.conversations.domain.errors import ConversationNotFoundError
from hify.modules.conversations.domain.value_objects import MessageRole, normalize_idempotency_key
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class AppendAssistantMessageCommand:
    team_id: UUID
    conversation_id: UUID
    content: str
    source_run_id: UUID
    created_by: UUID


class AppendAssistantMessageHandler:
    def __init__(
        self,
        unit_of_work_factory: ConversationsUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: AppendAssistantMessageCommand) -> ConversationMessageInfo:
        idempotency_key = normalize_idempotency_key(
            f"run:{command.source_run_id}:assistant"
        )
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            conversation = await unit_of_work.conversations.get_by_id(command.conversation_id)
            if conversation is None or conversation.team_id != command.team_id:
                raise ConversationNotFoundError("conversation was not found")

            existing_message = await unit_of_work.messages.get_by_idempotency_key(
                team_id=command.team_id,
                conversation_id=command.conversation_id,
                idempotency_key=idempotency_key,
            )
            if existing_message is not None:
                return conversation_message_info_from_domain(existing_message)

            message = conversation.append_message(
                role=MessageRole.ASSISTANT,
                content=command.content,
                created_by=command.created_by,
                idempotency_key=idempotency_key,
                now=now,
            )
            await unit_of_work.conversations.save(conversation)
            await unit_of_work.messages.add(message)
            await unit_of_work.commit()

        return conversation_message_info_from_domain(message)


class ConversationWriterService(ConversationWriter):
    def __init__(self, append_assistant_message_handler: AppendAssistantMessageHandler) -> None:
        self._append_assistant_message_handler = append_assistant_message_handler

    async def append_assistant_message(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        content: str,
        source_run_id: UUID,
        created_by: UUID,
    ) -> ConversationMessageInfo:
        return await self._append_assistant_message_handler.handle(
            AppendAssistantMessageCommand(
                team_id=team_id,
                conversation_id=conversation_id,
                content=content,
                source_run_id=source_run_id,
                created_by=created_by,
            )
        )
