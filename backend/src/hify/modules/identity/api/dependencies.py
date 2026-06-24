from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException, Request, status

from hify.modules.identity.application.queries.authenticate_session import (
    AuthenticateSessionHandler,
    AuthenticateSessionQuery,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.domain.errors import IdentityAuthenticationError


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


class CookieSessionAuthenticator:
    def __init__(
        self,
        *,
        cookie_name: str,
        authenticate_session_handler: AuthenticateSessionHandler,
    ) -> None:
        self._cookie_name = cookie_name
        self._authenticate_session_handler = authenticate_session_handler

    async def authenticate(self, request: Request) -> ActorContext:
        token = request.cookies.get(self._cookie_name)
        if token is None or token.strip() == "":
            raise _authentication_required("authentication session cookie is missing")

        try:
            return await self._authenticate_session_handler.handle(
                AuthenticateSessionQuery(token=token),
            )
        except IdentityAuthenticationError as exc:
            raise _authentication_required(exc.message) from exc


def _authentication_required(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "IDENTITY_AUTHENTICATION_REQUIRED",
            "message": message,
        },
    )
