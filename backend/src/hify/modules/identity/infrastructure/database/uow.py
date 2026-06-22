from __future__ import annotations

from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.identity.application.ports import IdentityUnitOfWork
from hify.modules.identity.infrastructure.database.repositories import (
    SqlAlchemyMembershipRepository,
    SqlAlchemyTeamRepository,
    SqlAlchemyUserRepository,
)


class SqlAlchemyIdentityUnitOfWork(IdentityUnitOfWork):
    users: SqlAlchemyUserRepository
    teams: SqlAlchemyTeamRepository
    memberships: SqlAlchemyMembershipRepository

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self._session = self._session_factory()
        self.users = SqlAlchemyUserRepository(self._session)
        self.teams = SqlAlchemyTeamRepository(self._session)
        self.memberships = SqlAlchemyMembershipRepository(self._session)
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
