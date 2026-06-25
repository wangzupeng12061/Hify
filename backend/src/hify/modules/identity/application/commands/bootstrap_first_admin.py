from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from hify.modules.identity.application.dto import AuthSessionResult
from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.application.session_tokens import SessionTokenService
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.domain.entities import AuthSession, Team, TeamMembership, User
from hify.modules.identity.domain.errors import (
    FirstAdminAlreadyBootstrappedError,
    IdentityAuthenticationError,
)
from hify.modules.identity.domain.value_objects import (
    EmailAddress,
    MembershipStatus,
    TeamRole,
    TeamStatus,
    UserStatus,
    normalize_team_name,
)
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class BootstrapFirstAdminCommand:
    email: str
    display_name: str
    team_name: str
    ttl_seconds: int


class BootstrapFirstAdminHandler:
    def __init__(
        self,
        unit_of_work_factory: IdentityUnitOfWorkFactory,
        clock: Clock,
        session_tokens: SessionTokenService,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._session_tokens = session_tokens

    async def handle(self, command: BootstrapFirstAdminCommand) -> AuthSessionResult:
        if command.ttl_seconds <= 0:
            raise IdentityAuthenticationError("session ttl must be positive")

        now = self._clock.now()
        email = EmailAddress.parse(command.email)
        team_name = normalize_team_name(command.team_name)
        token_pair = self._session_tokens.issue()

        async with self._unit_of_work_factory() as unit_of_work:
            if await unit_of_work.memberships.has_active_owner():
                raise FirstAdminAlreadyBootstrappedError(
                    "first administrator has already been bootstrapped"
                )

            user = await unit_of_work.users.get_by_email(email)
            if user is None:
                user = User.create(email=email, display_name=command.display_name, now=now)
                await unit_of_work.users.add(user)
            elif user.status != UserStatus.ACTIVE:
                raise IdentityAuthenticationError("bootstrap user is not active")

            team = await unit_of_work.teams.get_by_name(team_name)
            if team is None:
                team = Team.create(name=team_name, now=now)
                await unit_of_work.teams.add(team)
            elif team.status != TeamStatus.ACTIVE:
                raise IdentityAuthenticationError("bootstrap team is not active")

            membership = await unit_of_work.memberships.get_by_team_and_user(
                team_id=team.id,
                user_id=user.id,
            )
            if membership is None:
                membership = TeamMembership.create(
                    team_id=team.id,
                    user_id=user.id,
                    role=TeamRole.OWNER,
                    now=now,
                )
                await unit_of_work.memberships.add(membership)
            elif membership.status != MembershipStatus.ACTIVE:
                raise IdentityAuthenticationError("bootstrap membership is not active")
            elif membership.role != TeamRole.OWNER:
                raise IdentityAuthenticationError("bootstrap membership is not an owner")

            expires_at = now + timedelta(seconds=command.ttl_seconds)
            session = AuthSession.create(
                user_id=user.id,
                team_id=team.id,
                session_token_hash=token_pair.token_hash,
                expires_at=expires_at,
                now=now,
            )
            await unit_of_work.sessions.add(session)
            await unit_of_work.commit()

        return AuthSessionResult(
            token=token_pair.token,
            actor=ActorContext(
                user_id=user.id,
                team_id=team.id,
                membership_id=membership.id,
                role=membership.role.value,
                permissions=tuple(
                    permission.value for permission in sorted(membership.role.permissions)
                ),
            ),
            expires_at=expires_at,
        )
