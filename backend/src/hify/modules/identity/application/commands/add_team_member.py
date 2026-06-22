from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.application.authorization import require_permission
from hify.modules.identity.application.dto import membership_profile_from_domain
from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.contracts.dto import ActorContext, MembershipProfile
from hify.modules.identity.domain.entities import TeamMembership
from hify.modules.identity.domain.errors import (
    MembershipAlreadyExistsError,
    TeamNotFoundError,
    UserNotFoundError,
)
from hify.modules.identity.domain.value_objects import IdentityPermission, UserStatus, parse_team_role
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class AddTeamMemberCommand:
    actor: ActorContext
    team_id: UUID
    user_id: UUID
    role: str


class AddTeamMemberHandler:
    def __init__(self, unit_of_work_factory: IdentityUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: AddTeamMemberCommand) -> MembershipProfile:
        require_permission(command.actor, IdentityPermission.MANAGE_MEMBERS)
        if command.actor.team_id != command.team_id:
            raise TeamNotFoundError("team was not found")

        role = parse_team_role(command.role)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            team = await unit_of_work.teams.get_by_id(command.team_id)
            if team is None:
                raise TeamNotFoundError("team was not found")

            user = await unit_of_work.users.get_by_id(command.user_id)
            if user is None or user.status != UserStatus.ACTIVE:
                raise UserNotFoundError("user was not found")

            existing_membership = await unit_of_work.memberships.get_by_team_and_user(
                team_id=command.team_id,
                user_id=command.user_id,
            )
            if existing_membership is not None:
                raise MembershipAlreadyExistsError("team membership already exists")

            membership = TeamMembership.create(
                team_id=command.team_id,
                user_id=command.user_id,
                role=role,
                now=now,
            )
            await unit_of_work.memberships.add(membership)
            await unit_of_work.commit()

        return membership_profile_from_domain(membership)
