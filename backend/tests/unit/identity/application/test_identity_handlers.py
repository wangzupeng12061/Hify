from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.application.commands.add_team_member import (
    AddTeamMemberCommand,
    AddTeamMemberHandler,
)
from hify.modules.identity.application.commands.create_team import CreateTeamCommand, CreateTeamHandler
from hify.modules.identity.application.commands.create_user import CreateUserCommand, CreateUserHandler
from hify.modules.identity.application.queries.get_actor_context import (
    GetActorContextHandler,
    GetActorContextQuery,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.domain.entities import Team, TeamMembership, User
from hify.modules.identity.domain.errors import (
    IdentityPermissionDeniedError,
    MembershipAlreadyExistsError,
    UserEmailAlreadyExistsError,
)
from hify.modules.identity.domain.value_objects import EmailAddress, TeamRole
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeUserRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, User] = {}

    async def add(self, user: User) -> None:
        self.items[user.id] = user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self.items.get(user_id)

    async def get_by_email(self, email: EmailAddress) -> User | None:
        for user in self.items.values():
            if user.email == email:
                return user
        return None


class FakeTeamRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Team] = {}

    async def add(self, team: Team) -> None:
        self.items[team.id] = team

    async def get_by_id(self, team_id: UUID) -> Team | None:
        return self.items.get(team_id)

    async def get_by_name(self, name: str) -> Team | None:
        for team in self.items.values():
            if team.name == name:
                return team
        return None


class FakeMembershipRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, TeamMembership] = {}

    async def add(self, membership: TeamMembership) -> None:
        self.items[membership.id] = membership

    async def get_by_id(self, membership_id: UUID) -> TeamMembership | None:
        return self.items.get(membership_id)

    async def get_by_team_and_user(self, *, team_id: UUID, user_id: UUID) -> TeamMembership | None:
        for membership in self.items.values():
            if membership.team_id == team_id and membership.user_id == user_id:
                return membership
        return None


class FakeIdentityUnitOfWork:
    def __init__(self) -> None:
        self.users = FakeUserRepository()
        self.teams = FakeTeamRepository()
        self.memberships = FakeMembershipRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


@pytest.mark.asyncio
async def test_create_user_rejects_duplicate_email() -> None:
    unit_of_work = FakeIdentityUnitOfWork()
    handler = CreateUserHandler(lambda: unit_of_work, FixedClock())
    command = CreateUserCommand(email="owner@example.com", display_name="Owner")
    await handler.handle(command)

    with pytest.raises(UserEmailAlreadyExistsError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_create_team_creates_owner_membership() -> None:
    unit_of_work = FakeIdentityUnitOfWork()
    create_user_handler = CreateUserHandler(lambda: unit_of_work, FixedClock())
    owner = await create_user_handler.handle(
        CreateUserCommand(email="owner@example.com", display_name="Owner")
    )
    create_team_handler = CreateTeamHandler(lambda: unit_of_work, FixedClock())

    team = await create_team_handler.handle(
        CreateTeamCommand(name="Platform", owner_user_id=owner.id)
    )

    membership = await unit_of_work.memberships.get_by_team_and_user(
        team_id=team.id,
        user_id=owner.id,
    )
    assert membership is not None
    assert membership.role == TeamRole.OWNER


@pytest.mark.asyncio
async def test_get_actor_context_requires_active_membership() -> None:
    unit_of_work = FakeIdentityUnitOfWork()
    user_handler = CreateUserHandler(lambda: unit_of_work, FixedClock())
    owner = await user_handler.handle(CreateUserCommand(email="owner@example.com", display_name="Owner"))
    team_handler = CreateTeamHandler(lambda: unit_of_work, FixedClock())
    team = await team_handler.handle(CreateTeamCommand(name="Platform", owner_user_id=owner.id))

    handler = GetActorContextHandler(lambda: unit_of_work)
    actor = await handler.handle(GetActorContextQuery(user_id=owner.id, team_id=team.id))

    assert actor.user_id == owner.id
    assert actor.team_id == team.id
    assert "identity.members.manage" in actor.permissions


@pytest.mark.asyncio
async def test_add_team_member_requires_permission_and_prevents_duplicates() -> None:
    unit_of_work = FakeIdentityUnitOfWork()
    user_handler = CreateUserHandler(lambda: unit_of_work, FixedClock())
    owner = await user_handler.handle(CreateUserCommand(email="owner@example.com", display_name="Owner"))
    member = await user_handler.handle(
        CreateUserCommand(email="member@example.com", display_name="Member")
    )
    team_handler = CreateTeamHandler(lambda: unit_of_work, FixedClock())
    team = await team_handler.handle(CreateTeamCommand(name="Platform", owner_user_id=owner.id))
    actor = await GetActorContextHandler(lambda: unit_of_work).handle(
        GetActorContextQuery(user_id=owner.id, team_id=team.id)
    )
    handler = AddTeamMemberHandler(lambda: unit_of_work, FixedClock())

    created = await handler.handle(
        AddTeamMemberCommand(actor=actor, team_id=team.id, user_id=member.id, role="member")
    )

    assert created.user_id == member.id
    with pytest.raises(MembershipAlreadyExistsError):
        await handler.handle(
            AddTeamMemberCommand(actor=actor, team_id=team.id, user_id=member.id, role="member")
        )


@pytest.mark.asyncio
async def test_add_team_member_rejects_actor_without_permission() -> None:
    unit_of_work = FakeIdentityUnitOfWork()
    team_id = UUID("00000000-0000-7000-8000-000000000001")
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000002"),
        team_id=team_id,
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=("identity.members.read",),
    )
    handler = AddTeamMemberHandler(lambda: unit_of_work, FixedClock())

    with pytest.raises(IdentityPermissionDeniedError):
        await handler.handle(
            AddTeamMemberCommand(
                actor=actor,
                team_id=team_id,
                user_id=UUID("00000000-0000-7000-8000-000000000004"),
                role="member",
            )
        )
