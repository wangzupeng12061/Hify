from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.application.ports import IdentityUnitOfWorkFactory
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.contracts.services import IdentityAccess
from hify.modules.identity.domain.errors import IdentityPermissionDeniedError
from hify.modules.identity.domain.value_objects import MembershipStatus, TeamStatus, UserStatus


@dataclass(frozen=True, slots=True)
class GetActorContextQuery:
    user_id: UUID
    team_id: UUID


class GetActorContextHandler:
    def __init__(self, unit_of_work_factory: IdentityUnitOfWorkFactory) -> None:
        self._unit_of_work_factory = unit_of_work_factory

    async def handle(self, query: GetActorContextQuery) -> ActorContext:
        async with self._unit_of_work_factory() as unit_of_work:
            user = await unit_of_work.users.get_by_id(query.user_id)
            team = await unit_of_work.teams.get_by_id(query.team_id)
            membership = await unit_of_work.memberships.get_by_team_and_user(
                team_id=query.team_id,
                user_id=query.user_id,
            )

        if (
            user is None
            or team is None
            or membership is None
            or user.status != UserStatus.ACTIVE
            or team.status != TeamStatus.ACTIVE
            or membership.status != MembershipStatus.ACTIVE
        ):
            raise IdentityPermissionDeniedError("actor is not allowed to access this team")

        return ActorContext(
            user_id=user.id,
            team_id=team.id,
            membership_id=membership.id,
            role=membership.role.value,
            permissions=tuple(permission.value for permission in sorted(membership.role.permissions)),
        )


class IdentityAccessService(IdentityAccess):
    def __init__(self, get_actor_context_handler: GetActorContextHandler) -> None:
        self._get_actor_context_handler = get_actor_context_handler

    async def get_actor_context(self, *, user_id: UUID, team_id: UUID) -> ActorContext:
        query = GetActorContextQuery(user_id=user_id, team_id=team_id)
        return await self._get_actor_context_handler.handle(query)

    async def require_permission(self, actor: ActorContext, permission: str) -> None:
        if not actor.has_permission(permission):
            raise IdentityPermissionDeniedError("actor does not have the required permission")
