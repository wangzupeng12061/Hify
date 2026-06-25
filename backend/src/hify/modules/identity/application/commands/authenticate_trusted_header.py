from __future__ import annotations

from dataclasses import dataclass

from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.domain.entities import TeamMembership, User
from hify.modules.identity.domain.errors import IdentityAuthenticationError
from hify.modules.identity.domain.value_objects import (
    EmailAddress,
    MembershipStatus,
    TeamRole,
    TeamStatus,
    UserStatus,
    normalize_team_name,
    parse_team_role,
)
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class AuthenticateTrustedHeaderCommand:
    email: str
    display_name: str | None
    team_name: str
    default_role: str


class AuthenticateTrustedHeaderHandler:
    def __init__(
        self,
        unit_of_work_factory: IdentityUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: AuthenticateTrustedHeaderCommand) -> ActorContext:
        now = self._clock.now()
        email = EmailAddress.parse(command.email)
        team_name = normalize_team_name(command.team_name)
        default_role = parse_team_role(command.default_role)
        if default_role == TeamRole.OWNER:
            raise IdentityAuthenticationError("trusted header default role cannot be owner")

        async with self._unit_of_work_factory() as unit_of_work:
            user = await unit_of_work.users.get_by_email(email)
            if user is None:
                user = User.create(
                    email=email,
                    display_name=command.display_name or email.value.partition("@")[0],
                    now=now,
                )
                await unit_of_work.users.add(user)
            elif user.status != UserStatus.ACTIVE:
                raise IdentityAuthenticationError("trusted header user is not active")

            team = await unit_of_work.teams.get_by_name(team_name)
            if team is None or team.status != TeamStatus.ACTIVE:
                raise IdentityAuthenticationError(
                    "trusted header team is missing or inactive; bootstrap first admin first"
                )

            membership = await unit_of_work.memberships.get_by_team_and_user(
                team_id=team.id,
                user_id=user.id,
            )
            if membership is None:
                membership = TeamMembership.create(
                    team_id=team.id,
                    user_id=user.id,
                    role=default_role,
                    now=now,
                )
                await unit_of_work.memberships.add(membership)
            elif membership.status != MembershipStatus.ACTIVE:
                raise IdentityAuthenticationError("trusted header membership is not active")

            await unit_of_work.commit()

        return ActorContext(
            user_id=user.id,
            team_id=team.id,
            membership_id=membership.id,
            role=membership.role.value,
            permissions=tuple(permission.value for permission in sorted(membership.role.permissions)),
        )
