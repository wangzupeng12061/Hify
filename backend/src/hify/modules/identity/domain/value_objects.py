from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from hify.modules.identity.domain.errors import IdentityValidationError


class IdentityPermission(StrEnum):
    MANAGE_TEAM = "identity.team.manage"
    MANAGE_MEMBERS = "identity.members.manage"
    READ_MEMBERS = "identity.members.read"
    MANAGE_PROVIDERS = "providers.manage"
    MANAGE_AGENTS = "agents.manage"
    RUN_AGENTS = "runs.execute"
    READ_RUNS = "runs.read"
    MANAGE_KNOWLEDGE = "knowledge.manage"
    MANAGE_TOOLS = "tools.manage"
    READ_TOOLS = "tools.read"
    READ_USAGE = "usage.read"
    MANAGE_USAGE = "usage.manage"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class TeamStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class TeamRole(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"

    @property
    def permissions(self) -> frozenset[IdentityPermission]:
        return ROLE_PERMISSIONS[self]


ROLE_PERMISSIONS: dict[TeamRole, frozenset[IdentityPermission]] = {
    TeamRole.OWNER: frozenset(IdentityPermission),
    TeamRole.ADMIN: frozenset(
        {
            IdentityPermission.MANAGE_MEMBERS,
            IdentityPermission.READ_MEMBERS,
            IdentityPermission.MANAGE_PROVIDERS,
            IdentityPermission.MANAGE_AGENTS,
            IdentityPermission.RUN_AGENTS,
            IdentityPermission.READ_RUNS,
            IdentityPermission.MANAGE_KNOWLEDGE,
            IdentityPermission.MANAGE_TOOLS,
            IdentityPermission.READ_TOOLS,
            IdentityPermission.READ_USAGE,
            IdentityPermission.MANAGE_USAGE,
        }
    ),
    TeamRole.MEMBER: frozenset(
        {
            IdentityPermission.READ_MEMBERS,
            IdentityPermission.RUN_AGENTS,
            IdentityPermission.READ_RUNS,
        }
    ),
    TeamRole.VIEWER: frozenset(
        {
            IdentityPermission.READ_MEMBERS,
            IdentityPermission.READ_RUNS,
        }
    ),
}


@dataclass(frozen=True, slots=True)
class EmailAddress:
    value: str

    @classmethod
    def parse(cls, value: str) -> EmailAddress:
        normalized = value.strip().lower()
        if not normalized or "@" not in normalized or len(normalized) > 320:
            raise IdentityValidationError("email must be a valid address")
        local_part, _, domain = normalized.partition("@")
        if not local_part or not domain or "." not in domain:
            raise IdentityValidationError("email must be a valid address")
        return cls(normalized)


def normalize_display_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise IdentityValidationError("display name must not be blank")
    if len(normalized) > 120:
        raise IdentityValidationError("display name must be at most 120 characters")
    return normalized


def normalize_team_name(value: str) -> str:
    normalized = " ".join(value.strip().split())
    if not normalized:
        raise IdentityValidationError("team name must not be blank")
    if len(normalized) > 120:
        raise IdentityValidationError("team name must be at most 120 characters")
    return normalized


def parse_team_role(value: str) -> TeamRole:
    try:
        return TeamRole(value)
    except ValueError as exc:
        raise IdentityValidationError("team role is invalid") from exc
