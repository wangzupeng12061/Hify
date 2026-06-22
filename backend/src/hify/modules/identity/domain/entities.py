from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hify.shared.domain.ids import new_uuid

from hify.modules.identity.domain.value_objects import (
    EmailAddress,
    IdentityPermission,
    MembershipStatus,
    TeamRole,
    TeamStatus,
    UserStatus,
    normalize_display_name,
    normalize_team_name,
)


@dataclass(slots=True)
class User:
    id: UUID
    email: EmailAddress
    display_name: str
    status: UserStatus
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, email: EmailAddress, display_name: str, now: datetime) -> User:
        name = normalize_display_name(display_name)
        return cls(
            id=new_uuid(),
            email=email,
            display_name=name,
            status=UserStatus.ACTIVE,
            version=0,
            created_at=now,
            updated_at=now,
        )

    def rename(self, display_name: str, *, now: datetime) -> None:
        self.display_name = normalize_display_name(display_name)
        self._mark_updated(now)

    def disable(self, *, now: datetime) -> None:
        if self.status == UserStatus.DISABLED:
            return
        self.status = UserStatus.DISABLED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class Team:
    id: UUID
    name: str
    status: TeamStatus
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(cls, *, name: str, now: datetime) -> Team:
        return cls(
            id=new_uuid(),
            name=normalize_team_name(name),
            status=TeamStatus.ACTIVE,
            version=0,
            created_at=now,
            updated_at=now,
        )

    def rename(self, name: str, *, now: datetime) -> None:
        self.name = normalize_team_name(name)
        self._mark_updated(now)

    def archive(self, *, now: datetime) -> None:
        if self.status == TeamStatus.ARCHIVED:
            return
        self.status = TeamStatus.ARCHIVED
        self._mark_updated(now)

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now


@dataclass(slots=True)
class TeamMembership:
    id: UUID
    team_id: UUID
    user_id: UUID
    role: TeamRole
    status: MembershipStatus
    version: int
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        team_id: UUID,
        user_id: UUID,
        role: TeamRole,
        now: datetime,
    ) -> TeamMembership:
        return cls(
            id=new_uuid(),
            team_id=team_id,
            user_id=user_id,
            role=role,
            status=MembershipStatus.ACTIVE,
            version=0,
            created_at=now,
            updated_at=now,
        )

    def change_role(self, role: TeamRole, *, now: datetime) -> None:
        if self.role == role:
            return
        self.role = role
        self._mark_updated(now)

    def disable(self, *, now: datetime) -> None:
        if self.status == MembershipStatus.DISABLED:
            return
        self.status = MembershipStatus.DISABLED
        self._mark_updated(now)

    def has_permission(self, permission: IdentityPermission) -> bool:
        return self.status == MembershipStatus.ACTIVE and permission in self.role.permissions

    def _mark_updated(self, now: datetime) -> None:
        self.version += 1
        self.updated_at = now
