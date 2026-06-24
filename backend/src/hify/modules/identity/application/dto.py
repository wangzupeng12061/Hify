from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.contracts.dto import MembershipProfile, TeamProfile, UserProfile
from hify.modules.identity.domain.entities import Team, TeamMembership, User


def user_profile_from_domain(user: User) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email.value,
        display_name=user.display_name,
        status=user.status.value,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )


def team_profile_from_domain(team: Team) -> TeamProfile:
    return TeamProfile(
        id=team.id,
        name=team.name,
        status=team.status.value,
        created_at=team.created_at,
        updated_at=team.updated_at,
    )


def membership_profile_from_domain(membership: TeamMembership) -> MembershipProfile:
    return MembershipProfile(
        id=membership.id,
        team_id=membership.team_id,
        user_id=membership.user_id,
        role=membership.role.value,
        status=membership.status.value,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
    )


@dataclass(frozen=True, slots=True)
class AuthSessionResult:
    token: str
    actor: ActorContext
    expires_at: datetime
