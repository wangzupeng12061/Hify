from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hify.modules.identity.domain.entities import Team, TeamMembership, User
from hify.modules.identity.domain.errors import IdentityValidationError
from hify.modules.identity.domain.value_objects import (
    EmailAddress,
    IdentityPermission,
    TeamRole,
    UserStatus,
)


def test_create_user_normalizes_email_and_display_name() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)

    user = User.create(
        email=EmailAddress.parse("  OWNER@Example.COM "),
        display_name="  Owner   User ",
        now=now,
    )

    assert user.email.value == "owner@example.com"
    assert user.display_name == "Owner User"
    assert user.status == UserStatus.ACTIVE
    assert user.version == 0


def test_team_membership_permissions_follow_role() -> None:
    now = datetime(2026, 6, 22, tzinfo=UTC)
    team = Team.create(name="Platform", now=now)
    user = User.create(
        email=EmailAddress.parse("member@example.com"),
        display_name="Member",
        now=now,
    )

    membership = TeamMembership.create(
        team_id=team.id,
        user_id=user.id,
        role=TeamRole.MEMBER,
        now=now,
    )

    assert membership.has_permission(IdentityPermission.RUN_AGENTS)
    assert not membership.has_permission(IdentityPermission.MANAGE_MEMBERS)


def test_email_rejects_invalid_address() -> None:
    with pytest.raises(IdentityValidationError, match="email"):
        EmailAddress.parse("not-an-email")
