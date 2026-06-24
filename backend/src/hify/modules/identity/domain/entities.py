from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from hify.shared.domain.ids import new_uuid

from hify.modules.identity.domain.errors import IdentityValidationError
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


@dataclass(slots=True)
class AuthSession:
    id: UUID
    user_id: UUID
    team_id: UUID
    session_token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        user_id: UUID,
        team_id: UUID,
        session_token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> AuthSession:
        return cls(
            id=new_uuid(),
            user_id=user_id,
            team_id=team_id,
            session_token_hash=_validate_session_token_hash(session_token_hash),
            expires_at=expires_at,
            revoked_at=None,
            last_seen_at=now,
            created_at=now,
            updated_at=now,
        )

    def is_active(self, *, now: datetime) -> bool:
        return self.revoked_at is None and self.expires_at > now

    def mark_seen(self, *, now: datetime) -> None:
        self.last_seen_at = now
        self.updated_at = now

    def revoke(self, *, now: datetime) -> None:
        if self.revoked_at is not None:
            return
        self.revoked_at = now
        self.updated_at = now


@dataclass(slots=True)
class ExternalAccount:
    id: UUID
    provider: str
    subject: str
    user_id: UUID
    email: EmailAddress
    display_name: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def create(
        cls,
        *,
        provider: str,
        subject: str,
        user_id: UUID,
        email: EmailAddress,
        display_name: str,
        now: datetime,
    ) -> ExternalAccount:
        return cls(
            id=new_uuid(),
            provider=_normalize_external_value(provider, field_name="provider"),
            subject=_normalize_external_value(subject, field_name="subject"),
            user_id=user_id,
            email=email,
            display_name=normalize_display_name(display_name),
            created_at=now,
            updated_at=now,
        )


def _validate_session_token_hash(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise IdentityValidationError("session token hash must not be blank")
    return normalized


def _normalize_external_value(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise IdentityValidationError(f"{field_name} must not be blank")
    return normalized
