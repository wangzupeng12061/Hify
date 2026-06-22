from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.domain.errors import IdentityPermissionDeniedError
from hify.modules.identity.domain.value_objects import IdentityPermission


def require_permission(actor: ActorContext, permission: IdentityPermission) -> None:
    if not actor.has_permission(permission.value):
        raise IdentityPermissionDeniedError("actor does not have the required permission")
