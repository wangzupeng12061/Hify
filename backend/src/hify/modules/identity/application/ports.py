from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.identity.domain.repositories import (
    AuthSessionRepository,
    ExternalAccountRepository,
    MembershipRepository,
    TeamRepository,
    UserRepository,
)
from hify.shared.application.uow import UnitOfWork


class IdentityUnitOfWork(UnitOfWork, Protocol):
    users: UserRepository
    teams: TeamRepository
    memberships: MembershipRepository
    sessions: AuthSessionRepository
    external_accounts: ExternalAccountRepository

    async def __aenter__(self) -> Self: ...


IdentityUnitOfWorkFactory = Callable[[], IdentityUnitOfWork]
