from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException, Request, status

from hify.modules.identity.contracts.dto import ActorContext


class RequestAuthenticator(Protocol):
    async def authenticate(self, request: Request) -> ActorContext: ...


class AuthenticationNotConfiguredAuthenticator:
    async def authenticate(self, request: Request) -> ActorContext:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "AUTHENTICATION_NOT_CONFIGURED",
                "message": "authentication is not configured for this API",
            },
        )
