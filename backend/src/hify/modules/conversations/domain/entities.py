from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hify.modules.conversations.domain.value_objects import (
    ConversationStatus,
    MessageFeedbackRating,
    MessageRole,
    MessageStatus,
    normalize_conversation_title,
    normalize_feedback_comment,
    normalize_idempotency_key,
    normalize_message_content,
)
from hify.shared.domain.ids import new_uuid


@dataclass(slots=True)
class Conversation:
    id: UUID
    team_id: UUID
    agent_id: UUID
    title: str | None
    status: ConversationStatus
    message_count: int
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        agent_id: UUID,
        title: str | None,
        created_by: UUID,
        now: datetime,
    ) -> Conversation:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            agent_id=agent_id,
            title=normalize_conversation_title(title),
            status=ConversationStatus.ACTIVE,
            message_count=0,
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def append_message(
        self,
        *,
        role: MessageRole,
        content: str,
        created_by: UUID,
        idempotency_key: str,
        now: datetime,
    ) -> ConversationMessage:
        self.message_count += 1
        self._mark_updated(now)
        return ConversationMessage.create(
            team_id=self.team_id,
            conversation_id=self.id,
            sequence_number=self.message_count,
            role=role,
            content=content,
            created_by=created_by,
            idempotency_key=idempotency_key,
            now=now,
        )

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class ConversationMessage:
    id: UUID
    team_id: UUID
    conversation_id: UUID
    sequence_number: int
    role: MessageRole
    content: str
    status: MessageStatus
    idempotency_key: str
    created_by: UUID
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        conversation_id: UUID,
        sequence_number: int,
        role: MessageRole,
        content: str,
        created_by: UUID,
        idempotency_key: str,
        now: datetime,
    ) -> ConversationMessage:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            conversation_id=conversation_id,
            sequence_number=sequence_number,
            role=role,
            content=normalize_message_content(content),
            status=MessageStatus.CREATED,
            idempotency_key=normalize_idempotency_key(idempotency_key),
            created_by=created_by,
            created_at=now,
        )


@dataclass(slots=True)
class MessageFeedback:
    id: UUID
    team_id: UUID
    conversation_id: UUID
    message_id: UUID
    rating: MessageFeedbackRating
    comment: str | None
    version: int
    created_by: UUID
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        conversation_id: UUID,
        message_id: UUID,
        rating: MessageFeedbackRating,
        comment: str | None,
        created_by: UUID,
        now: datetime,
    ) -> MessageFeedback:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            conversation_id=conversation_id,
            message_id=message_id,
            rating=rating,
            comment=normalize_feedback_comment(comment),
            version=0,
            created_by=created_by,
            created_at=now,
            updated_at=now,
        )

    def update(
        self,
        *,
        rating: MessageFeedbackRating,
        comment: str | None,
        now: datetime,
    ) -> None:
        self.rating = rating
        self.comment = normalize_feedback_comment(comment)
        self.version += 1
        self.updated_at = now
