from __future__ import annotations

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.domain.errors import ProviderPermissionDeniedError


MANAGE_PROVIDERS_PERMISSION = "providers.manage"


def require_manage_providers(actor: ActorContext) -> None:
    if not actor.has_permission(MANAGE_PROVIDERS_PERMISSION):
        raise ProviderPermissionDeniedError("actor does not have permission to manage providers")
