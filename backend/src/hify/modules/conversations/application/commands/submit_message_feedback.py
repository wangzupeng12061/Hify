from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.conversations.application.authorization import require_execute_conversations
from hify.modules.conversations.application.dto import message_feedback_info_from_domain
from hify.modules.conversations.application.ports import ConversationsUnitOfWorkFactory
from hify.modules.conversations.contracts.dto import MessageFeedbackInfo
from hify.modules.conversations.domain.entities import MessageFeedback
from hify.modules.conversations.domain.errors import ConversationMessageNotFoundError
from hify.modules.conversations.domain.value_objects import MessageFeedbackRating
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class SubmitMessageFeedbackCommand:
    actor: ActorContext
    conversation_id: UUID
    message_id: UUID
    rating: str
    comment: str | None


class SubmitMessageFeedbackHandler:
    def __init__(
        self,
        unit_of_work_factory: ConversationsUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: SubmitMessageFeedbackCommand) -> MessageFeedbackInfo:
        require_execute_conversations(command.actor)
        now = self._clock.now()
        rating = MessageFeedbackRating(command.rating)

        async with self._unit_of_work_factory() as unit_of_work:
            message = await unit_of_work.messages.get_by_id(command.message_id)
            if (
                message is None
                or message.team_id != command.actor.team_id
                or message.conversation_id != command.conversation_id
            ):
                raise ConversationMessageNotFoundError("conversation message was not found")

            feedback = await unit_of_work.feedback.get_by_message_and_user(
                message_id=command.message_id,
                created_by=command.actor.user_id,
            )
            if feedback is None:
                feedback = MessageFeedback.create(
                    team_id=message.team_id,
                    conversation_id=message.conversation_id,
                    message_id=message.id,
                    rating=rating,
                    comment=command.comment,
                    created_by=command.actor.user_id,
                    now=now,
                )
                await unit_of_work.feedback.add(feedback)
            else:
                feedback.update(rating=rating, comment=command.comment, now=now)
                await unit_of_work.feedback.save(feedback)
            await unit_of_work.commit()
        return message_feedback_info_from_domain(feedback)
