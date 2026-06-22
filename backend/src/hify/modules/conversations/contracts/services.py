from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.conversations.contracts.dto import (
    ConversationInfo,
    ConversationMessagePage,
)


class ConversationReader(Protocol):
    async def get_conversation(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
    ) -> ConversationInfo: ...

    async def list_messages(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        cursor: str | None,
        limit: int,
    ) -> ConversationMessagePage: ...
