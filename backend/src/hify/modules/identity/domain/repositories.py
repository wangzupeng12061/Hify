from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.identity.domain.entities import AuthSession, ExternalAccount, Team, TeamMembership, User
from hify.modules.identity.domain.value_objects import EmailAddress


class UserRepository(Protocol):
    async def add(self, user: User) -> None: ...

    async def get_by_id(self, user_id: UUID) -> User | None: ...

    async def get_by_email(self, email: EmailAddress) -> User | None: ...


class TeamRepository(Protocol):
    async def add(self, team: Team) -> None: ...

    async def get_by_id(self, team_id: UUID) -> Team | None: ...

    async def get_by_name(self, name: str) -> Team | None: ...


class MembershipRepository(Protocol):
    async def add(self, membership: TeamMembership) -> None: ...

    async def get_by_id(self, membership_id: UUID) -> TeamMembership | None: ...

    async def get_by_team_and_user(self, *, team_id: UUID, user_id: UUID) -> TeamMembership | None:
        ...


class AuthSessionRepository(Protocol):
    async def add(self, session: AuthSession) -> None: ...

    async def get_by_token_hash(self, session_token_hash: str) -> AuthSession | None: ...

    async def save(self, session: AuthSession) -> None: ...


class ExternalAccountRepository(Protocol):
    async def add(self, account: ExternalAccount) -> None: ...

    async def get_by_provider_subject(
        self,
        *,
        provider: str,
        subject: str,
    ) -> ExternalAccount | None: ...
