from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.conversations.application.ports import ConversationsUnitOfWork
from hify.modules.conversations.infrastructure.database.repositories import (
    SqlAlchemyConversationMessageRepository,
    SqlAlchemyConversationRepository,
    SqlAlchemyMessageFeedbackRepository,
)


class SqlAlchemyConversationsUnitOfWork(ConversationsUnitOfWork):
    conversations: SqlAlchemyConversationRepository
    messages: SqlAlchemyConversationMessageRepository
    feedback: SqlAlchemyMessageFeedbackRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.conversations = SqlAlchemyConversationRepository(self._session)
        self.messages = SqlAlchemyConversationMessageRepository(self._session)
        self.feedback = SqlAlchemyMessageFeedbackRepository(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._session is None:
            return
        try:
            if exc_type is not None:
                await self.rollback()
        finally:
            await self._session.close()

    async def commit(self) -> None:
        if self._session is None:
            raise RuntimeError("unit of work has not been entered")
        await self._session.commit()

    async def rollback(self) -> None:
        if self._session is None:
            raise RuntimeError("unit of work has not been entered")
        await self._session.rollback()
