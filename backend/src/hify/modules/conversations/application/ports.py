from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.conversations.domain.repositories import (
    ConversationMessageRepository,
    ConversationRepository,
    MessageFeedbackRepository,
)
from hify.shared.application.uow import UnitOfWork


class ConversationsUnitOfWork(UnitOfWork, Protocol):
    conversations: ConversationRepository
    messages: ConversationMessageRepository
    feedback: MessageFeedbackRepository

    async def __aenter__(self) -> Self: ...


ConversationsUnitOfWorkFactory = Callable[[], ConversationsUnitOfWork]
