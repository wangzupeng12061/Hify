from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.conversations.domain.entities import (
    Conversation,
    ConversationMessage,
    MessageFeedback,
)
from hify.modules.conversations.domain.value_objects import (
    ConversationStatus,
    MessageFeedbackRating,
    MessageRole,
    MessageStatus,
)
from hify.modules.conversations.infrastructure.database.models import (
    ConversationMessageModel,
    ConversationModel,
    MessageFeedbackModel,
)


class SqlAlchemyConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, conversation: Conversation) -> None:
        self._session.add(_conversation_to_model(conversation))

    async def save(self, conversation: Conversation) -> None:
        model = await self._session.get(ConversationModel, conversation.id)
        if model is None:
            self._session.add(_conversation_to_model(conversation))
            return
        model.title = conversation.title
        model.status = conversation.status.value
        model.message_count = conversation.message_count
        model.version = conversation.version
        model.updated_at = conversation.updated_at

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None:
        model = await self._session.get(ConversationModel, conversation_id)
        if model is None:
            return None
        return _conversation_from_model(model)


class SqlAlchemyConversationMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: ConversationMessage) -> None:
        self._session.add(_message_to_model(message))

    async def get_by_id(self, message_id: UUID) -> ConversationMessage | None:
        model = await self._session.get(ConversationMessageModel, message_id)
        if model is None:
            return None
        return _message_from_model(model)

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
    ) -> ConversationMessage | None:
        statement = select(ConversationMessageModel).where(
            ConversationMessageModel.team_id == team_id,
            ConversationMessageModel.conversation_id == conversation_id,
            ConversationMessageModel.idempotency_key == idempotency_key,
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _message_from_model(model)

    async def list_by_conversation(
        self,
        *,
        conversation_id: UUID,
        after_sequence_number: int | None,
        limit: int,
    ) -> tuple[ConversationMessage, ...]:
        statement = (
            select(ConversationMessageModel)
            .where(ConversationMessageModel.conversation_id == conversation_id)
            .order_by(ConversationMessageModel.sequence_number.asc())
            .limit(limit)
        )
        if after_sequence_number is not None:
            statement = statement.where(
                ConversationMessageModel.sequence_number > after_sequence_number
            )
        models = (await self._session.scalars(statement)).all()
        return tuple(_message_from_model(model) for model in models)


class SqlAlchemyMessageFeedbackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, feedback: MessageFeedback) -> None:
        self._session.add(_feedback_to_model(feedback))

    async def save(self, feedback: MessageFeedback) -> None:
        model = await self._session.get(MessageFeedbackModel, feedback.id)
        if model is None:
            self._session.add(_feedback_to_model(feedback))
            return
        model.rating = feedback.rating.value
        model.comment = feedback.comment
        model.version = feedback.version
        model.updated_at = feedback.updated_at

    async def get_by_message_and_user(
        self,
        *,
        message_id: UUID,
        created_by: UUID,
    ) -> MessageFeedback | None:
        statement = select(MessageFeedbackModel).where(
            MessageFeedbackModel.message_id == message_id,
            MessageFeedbackModel.created_by == created_by,
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _feedback_from_model(model)


def _conversation_to_model(conversation: Conversation) -> ConversationModel:
    return ConversationModel(
        id=conversation.id,
        team_id=conversation.team_id,
        agent_id=conversation.agent_id,
        title=conversation.title,
        status=conversation.status.value,
        message_count=conversation.message_count,
        version=conversation.version,
        created_by=conversation.created_by,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


def _conversation_from_model(model: ConversationModel) -> Conversation:
    return Conversation(
        id=model.id,
        team_id=model.team_id,
        agent_id=model.agent_id,
        title=model.title,
        status=ConversationStatus(model.status),
        message_count=model.message_count,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _message_to_model(message: ConversationMessage) -> ConversationMessageModel:
    return ConversationMessageModel(
        id=message.id,
        team_id=message.team_id,
        conversation_id=message.conversation_id,
        sequence_number=message.sequence_number,
        role=message.role.value,
        content=message.content,
        status=message.status.value,
        idempotency_key=message.idempotency_key,
        created_by=message.created_by,
        created_at=message.created_at,
    )


def _message_from_model(model: ConversationMessageModel) -> ConversationMessage:
    return ConversationMessage(
        id=model.id,
        team_id=model.team_id,
        conversation_id=model.conversation_id,
        sequence_number=model.sequence_number,
        role=MessageRole(model.role),
        content=model.content,
        status=MessageStatus(model.status),
        idempotency_key=model.idempotency_key,
        created_by=model.created_by,
        created_at=model.created_at,
    )


def _feedback_to_model(feedback: MessageFeedback) -> MessageFeedbackModel:
    return MessageFeedbackModel(
        id=feedback.id,
        team_id=feedback.team_id,
        conversation_id=feedback.conversation_id,
        message_id=feedback.message_id,
        rating=feedback.rating.value,
        comment=feedback.comment,
        version=feedback.version,
        created_by=feedback.created_by,
        created_at=feedback.created_at,
        updated_at=feedback.updated_at,
    )


def _feedback_from_model(model: MessageFeedbackModel) -> MessageFeedback:
    return MessageFeedback(
        id=model.id,
        team_id=model.team_id,
        conversation_id=model.conversation_id,
        message_id=model.message_id,
        rating=MessageFeedbackRating(model.rating),
        comment=model.comment,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
