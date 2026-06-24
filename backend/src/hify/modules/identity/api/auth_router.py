from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from hify.modules.identity.api.dependencies import RequestAuthenticator
from hify.modules.identity.api.schemas import (
    ActorContextResponse,
    AuthSessionResponse,
    DevLoginRequest,
    OidcLoginResponse,
)
from hify.modules.identity.application.commands.create_dev_session import (
    CreateDevSessionCommand,
    CreateDevSessionHandler,
)
from hify.modules.identity.application.commands.revoke_session import (
    RevokeSessionCommand,
    RevokeSessionHandler,
)
from hify.modules.identity.contracts.dto import ActorContext


@dataclass(frozen=True, slots=True)
class AuthRouterConfig:
    cookie_name: str
    cookie_secure: bool
    cookie_samesite: Literal["lax", "strict", "none"]
    dev_login_enabled: bool
    session_ttl_seconds: int
    oidc_enabled: bool


def create_auth_router(
    *,
    config: AuthRouterConfig,
    create_dev_session_handler: CreateDevSessionHandler,
    revoke_session_handler: RevokeSessionHandler,
    request_authenticator: RequestAuthenticator,
) -> APIRouter:
    router = APIRouter(prefix="/auth", tags=["auth"])

    async def get_current_actor(request: Request) -> ActorContext:
        return await request_authenticator.authenticate(request)

    @router.post(
        "/dev/session",
        response_model=AuthSessionResponse,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_dev_session(
        request: DevLoginRequest,
        response: Response,
    ) -> AuthSessionResponse:
        if not config.dev_login_enabled:
            raise _auth_error(
                status.HTTP_403_FORBIDDEN,
                code="IDENTITY_DEV_LOGIN_DISABLED",
                message="developer login is disabled",
            )

        result = await create_dev_session_handler.handle(
            CreateDevSessionCommand(
                email=request.email,
                display_name=request.display_name,
                team_name=request.team_name,
                ttl_seconds=config.session_ttl_seconds,
            )
        )
        _set_session_cookie(response, config=config, token=result.token)
        return AuthSessionResponse(
            actor=_actor_response(result.actor),
            expires_at=result.expires_at,
        )

    @router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
    async def logout(request: Request, response: Response) -> None:
        token = request.cookies.get(config.cookie_name)
        if token is not None and token.strip() != "":
            await revoke_session_handler.handle(RevokeSessionCommand(token=token))
        response.delete_cookie(
            key=config.cookie_name,
            httponly=True,
            secure=config.cookie_secure,
            samesite=config.cookie_samesite,
            path="/",
        )

    @router.get("/me", response_model=ActorContextResponse)
    async def get_me(actor: ActorContext = Depends(get_current_actor)) -> ActorContextResponse:
        return _actor_response(actor)

    @router.get("/oidc/login", response_model=OidcLoginResponse)
    async def create_oidc_login() -> OidcLoginResponse:
        if not config.oidc_enabled:
            raise _oidc_not_implemented("OIDC login is not configured")
        raise _oidc_not_implemented("OIDC login flow is not implemented yet")

    @router.get("/oidc/callback", response_model=AuthSessionResponse)
    async def handle_oidc_callback() -> AuthSessionResponse:
        if not config.oidc_enabled:
            raise _oidc_not_implemented("OIDC callback is not configured")
        raise _oidc_not_implemented("OIDC callback flow is not implemented yet")

    return router


def _set_session_cookie(response: Response, *, config: AuthRouterConfig, token: str) -> None:
    response.set_cookie(
        key=config.cookie_name,
        value=token,
        max_age=config.session_ttl_seconds,
        httponly=True,
        secure=config.cookie_secure,
        samesite=config.cookie_samesite,
        path="/",
    )


def _actor_response(actor: ActorContext) -> ActorContextResponse:
    return ActorContextResponse(
        user_id=actor.user_id,
        team_id=actor.team_id,
        membership_id=actor.membership_id,
        role=actor.role,
        permissions=actor.permissions,
    )


def _oidc_not_implemented(message: str) -> HTTPException:
    return _auth_error(
        status.HTTP_501_NOT_IMPLEMENTED,
        code="IDENTITY_OIDC_NOT_IMPLEMENTED",
        message=message,
    )


def _auth_error(status_code: int, *, code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "message": message,
        },
    )
