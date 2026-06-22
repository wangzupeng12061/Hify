from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.identity.api.router import create_identity_router
from hify.modules.identity.application.commands.add_team_member import AddTeamMemberHandler
from hify.modules.identity.application.commands.create_team import CreateTeamHandler
from hify.modules.identity.application.commands.create_user import CreateUserHandler
from hify.modules.identity.application.queries.get_actor_context import (
    GetActorContextHandler,
    IdentityAccessService,
)
from hify.modules.identity.contracts.services import IdentityAccess
from hify.modules.identity.infrastructure.database.uow import SqlAlchemyIdentityUnitOfWork
from hify.shared.domain.clock import SystemClock


@dataclass(frozen=True, slots=True)
class IdentityModule:
    router: APIRouter
    identity_access: IdentityAccess


def create_identity_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    clock: SystemClock | None = None,
) -> IdentityModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyIdentityUnitOfWork:
        return SqlAlchemyIdentityUnitOfWork(session_factory)

    create_user_handler = CreateUserHandler(unit_of_work_factory, module_clock)
    create_team_handler = CreateTeamHandler(unit_of_work_factory, module_clock)
    add_team_member_handler = AddTeamMemberHandler(unit_of_work_factory, module_clock)
    get_actor_context_handler = GetActorContextHandler(unit_of_work_factory)
    identity_access = IdentityAccessService(get_actor_context_handler)

    router = create_identity_router(
        create_user_handler=create_user_handler,
        create_team_handler=create_team_handler,
        add_team_member_handler=add_team_member_handler,
        get_actor_context_handler=get_actor_context_handler,
    )

    return IdentityModule(router=router, identity_access=identity_access)
