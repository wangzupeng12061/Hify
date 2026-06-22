from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.application.dto import team_profile_from_domain
from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.contracts.dto import TeamProfile
from hify.modules.identity.domain.entities import Team, TeamMembership
from hify.modules.identity.domain.errors import TeamNameAlreadyExistsError, UserNotFoundError
from hify.modules.identity.domain.value_objects import TeamRole, UserStatus, normalize_team_name
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateTeamCommand:
    name: str
    owner_user_id: UUID


class CreateTeamHandler:
    def __init__(self, unit_of_work_factory: IdentityUnitOfWorkFactory, clock: Clock) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: CreateTeamCommand) -> TeamProfile:
        team_name = normalize_team_name(command.name)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            owner = await unit_of_work.users.get_by_id(command.owner_user_id)
            if owner is None or owner.status != UserStatus.ACTIVE:
                raise UserNotFoundError("owner user was not found")

            existing_team = await unit_of_work.teams.get_by_name(team_name)
            if existing_team is not None:
                raise TeamNameAlreadyExistsError("team name already exists")

            team = Team.create(name=team_name, now=now)
            membership = TeamMembership.create(
                team_id=team.id,
                user_id=owner.id,
                role=TeamRole.OWNER,
                now=now,
            )
            await unit_of_work.teams.add(team)
            await unit_of_work.memberships.add(membership)
            await unit_of_work.commit()

        return team_profile_from_domain(team)
