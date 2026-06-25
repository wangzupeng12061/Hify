from __future__ import annotations

from typing import Protocol

from fastapi import HTTPException, Request, status

from hify.modules.identity.application.commands.authenticate_trusted_header import (
    AuthenticateTrustedHeaderCommand,
    AuthenticateTrustedHeaderHandler,
)
from hify.modules.identity.application.queries.authenticate_session import (
    AuthenticateSessionHandler,
    AuthenticateSessionQuery,
)
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.identity.domain.errors import IdentityError


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
        except IdentityError as exc:
            raise _authentication_required(exc.message) from exc


class TrustedHeaderAuthenticator:
    def __init__(
        self,
        *,
        email_header_name: str,
        display_name_header_name: str,
        team_name: str,
        default_role: str,
        authenticate_trusted_header_handler: AuthenticateTrustedHeaderHandler,
    ) -> None:
        self._email_header_name = email_header_name
        self._display_name_header_name = display_name_header_name
        self._team_name = team_name
        self._default_role = default_role
        self._authenticate_trusted_header_handler = authenticate_trusted_header_handler

    async def authenticate(self, request: Request) -> ActorContext:
        email = request.headers.get(self._email_header_name)
        if email is None or email.strip() == "":
            raise _authentication_required("trusted identity header is missing")

        display_name = request.headers.get(self._display_name_header_name)
        try:
            return await self._authenticate_trusted_header_handler.handle(
                AuthenticateTrustedHeaderCommand(
                    email=email,
                    display_name=display_name,
                    team_name=self._team_name,
                    default_role=self._default_role,
                )
            )
        except IdentityError as exc:
            raise _authentication_required(exc.message) from exc


class CompositeRequestAuthenticator:
    def __init__(self, authenticators: tuple[RequestAuthenticator, ...]) -> None:
        self._authenticators = authenticators

    async def authenticate(self, request: Request) -> ActorContext:
        last_error: HTTPException | None = None
        for authenticator in self._authenticators:
            try:
                return await authenticator.authenticate(request)
            except HTTPException as exc:
                if exc.status_code != status.HTTP_401_UNAUTHORIZED:
                    raise
                last_error = exc

        if last_error is not None:
            raise last_error
        raise _authentication_required("authentication is not configured")


def _authentication_required(message: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "code": "IDENTITY_AUTHENTICATION_REQUIRED",
            "message": message,
        },
    )
