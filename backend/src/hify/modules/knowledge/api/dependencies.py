from __future__ import annotations

from typing import Protocol

from fastapi import Request

from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.errors import PermissionDeniedError


class RequestAuthenticator(Protocol):
    async def authenticate(self, request: Request) -> ActorContext: ...


class AuthenticationNotConfiguredAuthenticator:
    async def authenticate(self, request: Request) -> ActorContext:
        _ = request
        raise PermissionDeniedError("request authentication is not configured")
