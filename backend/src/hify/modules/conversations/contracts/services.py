from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.conversations.contracts.dto import (
    ConversationInfo,
    ConversationMessageInfo,
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


class ConversationWriter(Protocol):
    async def append_assistant_message(
        self,
        *,
        team_id: UUID,
        conversation_id: UUID,
        content: str,
        source_run_id: UUID,
        created_by: UUID,
    ) -> ConversationMessageInfo: ...
