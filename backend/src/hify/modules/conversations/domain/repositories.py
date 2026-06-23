from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from hify.modules.conversations.domain.entities import (
    Conversation,
    ConversationMessage,
    MessageFeedback,
)


class ConversationRepository(Protocol):
    async def add(self, conversation: Conversation) -> None: ...

    async def save(self, conversation: Conversation) -> None: ...

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...

    async def list_by_team(
        self,
        *,
        team_id: UUID,
        before: tuple[datetime, UUID] | None,
        limit: int,
    ) -> tuple[Conversation, ...]: ...


class ConversationMessageRepository(Protocol):
    async def add(self, message: ConversationMessage) -> None: ...

    async def get_by_id(self, message_id: UUID) -> ConversationMessage | None: ...

    async def get_by_idempotency_key(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        idempotency_key: str,
    ) -> ConversationMessage | None: ...

    async def list_by_conversation(
        self,
        *,
        conversation_id: UUID,
        after_sequence_number: int | None,
        limit: int,
    ) -> tuple[ConversationMessage, ...]: ...


class MessageFeedbackRepository(Protocol):
    async def add(self, feedback: MessageFeedback) -> None: ...

    async def save(self, feedback: MessageFeedback) -> None: ...

    async def get_by_message_and_user(
        self,
        *,
        message_id: UUID,
        created_by: UUID,
    ) -> MessageFeedback | None: ...
