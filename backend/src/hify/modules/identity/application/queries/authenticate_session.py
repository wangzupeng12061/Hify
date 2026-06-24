from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.application.session_tokens import SessionTokenService
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.domain.errors import IdentityAuthenticationError
from hify.modules.identity.domain.value_objects import MembershipStatus, TeamStatus, UserStatus
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class AuthenticateSessionQuery:
    token: str


class AuthenticateSessionHandler:
    def __init__(
        self,
        unit_of_work_factory: IdentityUnitOfWorkFactory,
        clock: Clock,
        session_tokens: SessionTokenService,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock
        self._session_tokens = session_tokens

    async def handle(self, query: AuthenticateSessionQuery) -> ActorContext:
        now = self._clock.now()
        token_hash = self._session_tokens.hash_token(query.token)

        async with self._unit_of_work_factory() as unit_of_work:
            session = await unit_of_work.sessions.get_by_token_hash(token_hash)
            if session is None or not session.is_active(now=now):
                raise IdentityAuthenticationError("session is missing, revoked, or expired")

            user = await unit_of_work.users.get_by_id(session.user_id)
            team = await unit_of_work.teams.get_by_id(session.team_id)
            membership = await unit_of_work.memberships.get_by_team_and_user(
                team_id=session.team_id,
                user_id=session.user_id,
            )
            if (
                user is None
                or team is None
                or membership is None
                or user.status != UserStatus.ACTIVE
                or team.status != TeamStatus.ACTIVE
                or membership.status != MembershipStatus.ACTIVE
            ):
                raise IdentityAuthenticationError("session actor is not active")

            session.mark_seen(now=now)
            await unit_of_work.sessions.save(session)
            await unit_of_work.commit()

        return ActorContext(
            user_id=user.id,
            team_id=team.id,
            membership_id=membership.id,
            role=membership.role.value,
            permissions=tuple(permission.value for permission in sorted(membership.role.permissions)),
        )
