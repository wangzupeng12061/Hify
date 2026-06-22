from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ActorContext:
    user_id: UUID
    team_id: UUID
    membership_id: UUID
    role: str
    permissions: tuple[str, ...]

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


@dataclass(frozen=True, slots=True)
class UserProfile:
    id: UUID
    email: str
    display_name: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TeamProfile:
    id: UUID
    name: str
    status: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class MembershipProfile:
    id: UUID
    team_id: UUID
    user_id: UUID
    role: str
    status: str
    created_at: datetime
    updated_at: datetime
