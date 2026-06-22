from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.identity.domain.entities import Team, TeamMembership, User
from hify.modules.identity.domain.value_objects import (
    EmailAddress,
    MembershipStatus,
    TeamRole,
    TeamStatus,
    UserStatus,
)
from hify.modules.identity.infrastructure.database.models import (
    TeamMembershipModel,
    TeamModel,
    UserModel,
)


class SqlAlchemyUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, user: User) -> None:
        self._session.add(_user_to_model(user))

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        if model is None:
            return None
        return _user_from_model(model)

    async def get_by_email(self, email: EmailAddress) -> User | None:
        statement = select(UserModel).where(func.lower(UserModel.email) == email.value)
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _user_from_model(model)


class SqlAlchemyTeamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, team: Team) -> None:
        self._session.add(_team_to_model(team))

    async def get_by_id(self, team_id: UUID) -> Team | None:
        model = await self._session.get(TeamModel, team_id)
        if model is None:
            return None
        return _team_from_model(model)

    async def get_by_name(self, name: str) -> Team | None:
        statement = select(TeamModel).where(func.lower(TeamModel.name) == name.lower())
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _team_from_model(model)


class SqlAlchemyMembershipRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, membership: TeamMembership) -> None:
        self._session.add(_membership_to_model(membership))

    async def get_by_id(self, membership_id: UUID) -> TeamMembership | None:
        model = await self._session.get(TeamMembershipModel, membership_id)
        if model is None:
            return None
        return _membership_from_model(model)

    async def get_by_team_and_user(self, *, team_id: UUID, user_id: UUID) -> TeamMembership | None:
        statement = select(TeamMembershipModel).where(
            TeamMembershipModel.team_id == team_id,
            TeamMembershipModel.user_id == user_id,
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _membership_from_model(model)


def _user_to_model(user: User) -> UserModel:
    return UserModel(
        id=user.id,
        email=user.email.value,
        display_name=user.display_name,
        status=user.status.value,
        version=user.version,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def _user_from_model(model: UserModel) -> User:
    return User(
        id=model.id,
        email=EmailAddress.parse(model.email),
        display_name=model.display_name,
        status=UserStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _team_to_model(team: Team) -> TeamModel:
    return TeamModel(
        id=team.id,
        name=team.name,
        status=team.status.value,
        version=team.version,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


def _team_from_model(model: TeamModel) -> Team:
    return Team(
        id=model.id,
        name=model.name,
        status=TeamStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _membership_to_model(membership: TeamMembership) -> TeamMembershipModel:
    return TeamMembershipModel(
        id=membership.id,
        team_id=membership.team_id,
        user_id=membership.user_id,
        role=membership.role.value,
        status=membership.status.value,
        version=membership.version,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


def _membership_from_model(model: TeamMembershipModel) -> TeamMembership:
    return TeamMembership(
        id=model.id,
        team_id=model.team_id,
        user_id=model.user_id,
        role=TeamRole(model.role),
        status=MembershipStatus(model.status),
        version=model.version,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )
