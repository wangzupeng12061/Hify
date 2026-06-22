from __future__ import annotations

from hify.modules.conversations.contracts.dto import (
    ConversationInfo,
    ConversationMessageInfo,
    MessageFeedbackInfo,
)
from hify.modules.conversations.domain.entities import (
    Conversation,
    ConversationMessage,
    MessageFeedback,
)


def conversation_info_from_domain(conversation: Conversation) -> ConversationInfo:
    return ConversationInfo(
        id=conversation.id,
        team_id=conversation.team_id,
        agent_id=conversation.agent_id,
        title=conversation.title,
        status=conversation.status.value,
        message_count=conversation.message_count,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def conversation_message_info_from_domain(
    message: ConversationMessage,
) -> ConversationMessageInfo:
    return ConversationMessageInfo(
        id=message.id,
        team_id=message.team_id,
        conversation_id=message.conversation_id,
        sequence_number=message.sequence_number,
        role=message.role.value,
        content=message.content,
        status=message.status.value,
        created_at=message.created_at,
    )


def message_feedback_info_from_domain(feedback: MessageFeedback) -> MessageFeedbackInfo:
    return MessageFeedbackInfo(
        id=feedback.id,
        team_id=feedback.team_id,
        conversation_id=feedback.conversation_id,
        message_id=feedback.message_id,
        rating=feedback.rating.value,
        comment=feedback.comment,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )
