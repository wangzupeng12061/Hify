from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.identity.api.auth_router import AuthRouterConfig, create_auth_router
from hify.modules.identity.api.dependencies import (
    CompositeRequestAuthenticator,
    CookieSessionAuthenticator,
    RequestAuthenticator,
    TrustedHeaderAuthenticator,
)
from hify.modules.identity.api.router import create_identity_router
from hify.modules.identity.application.commands.authenticate_trusted_header import (
    AuthenticateTrustedHeaderHandler,
)
from hify.modules.identity.application.commands.bootstrap_first_admin import BootstrapFirstAdminHandler
from hify.modules.identity.application.commands.create_dev_session import CreateDevSessionHandler
from hify.modules.identity.application.commands.revoke_session import RevokeSessionHandler
from hify.modules.identity.application.commands.add_team_member import AddTeamMemberHandler
from hify.modules.identity.application.commands.create_team import CreateTeamHandler
from hify.modules.identity.application.commands.create_user import CreateUserHandler
from hify.modules.identity.application.queries.get_actor_context import (
    GetActorContextHandler,
    IdentityAccessService,
)
from hify.modules.identity.application.queries.authenticate_session import AuthenticateSessionHandler
from hify.modules.identity.application.session_tokens import SessionTokenService
from hify.modules.identity.contracts.services import IdentityAccess
from hify.modules.identity.infrastructure.database.uow import SqlAlchemyIdentityUnitOfWork
from hify.shared.domain.clock import SystemClock


@dataclass(frozen=True, slots=True)
class IdentityModule:
    router: APIRouter
    identity_access: IdentityAccess
    request_authenticator: RequestAuthenticator


def create_identity_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    auth_cookie_name: str,
    auth_cookie_secure: bool,
    auth_cookie_samesite: Literal["lax", "strict", "none"],
    auth_session_ttl_seconds: int,
    auth_dev_login_enabled: bool,
    auth_oidc_enabled: bool,
    auth_bootstrap_token: str | None,
    auth_trusted_header_enabled: bool,
    auth_trusted_email_header: str,
    auth_trusted_display_name_header: str,
    auth_trusted_team_name: str,
    auth_trusted_default_role: Literal["admin", "member", "viewer"],
    clock: SystemClock | None = None,
) -> IdentityModule:
    module_clock = clock or SystemClock()
    session_tokens = SessionTokenService()

    def unit_of_work_factory() -> SqlAlchemyIdentityUnitOfWork:
        return SqlAlchemyIdentityUnitOfWork(session_factory)

    create_user_handler = CreateUserHandler(unit_of_work_factory, module_clock)
    create_team_handler = CreateTeamHandler(unit_of_work_factory, module_clock)
    add_team_member_handler = AddTeamMemberHandler(unit_of_work_factory, module_clock)
    get_actor_context_handler = GetActorContextHandler(unit_of_work_factory)
    identity_access = IdentityAccessService(get_actor_context_handler)
    authenticate_session_handler = AuthenticateSessionHandler(
        unit_of_work_factory,
        module_clock,
        session_tokens,
    )
    cookie_session_authenticator = CookieSessionAuthenticator(
        cookie_name=auth_cookie_name,
        authenticate_session_handler=authenticate_session_handler,
    )
    authenticators: list[RequestAuthenticator] = [cookie_session_authenticator]
    authenticate_trusted_header_handler = AuthenticateTrustedHeaderHandler(
        unit_of_work_factory,
        module_clock,
    )
    if auth_trusted_header_enabled:
        authenticators.append(
            TrustedHeaderAuthenticator(
                email_header_name=auth_trusted_email_header,
                display_name_header_name=auth_trusted_display_name_header,
                team_name=auth_trusted_team_name,
                default_role=auth_trusted_default_role,
                authenticate_trusted_header_handler=authenticate_trusted_header_handler,
            )
        )
    request_authenticator: RequestAuthenticator = CompositeRequestAuthenticator(tuple(authenticators))
    bootstrap_first_admin_handler = BootstrapFirstAdminHandler(
        unit_of_work_factory,
        module_clock,
        session_tokens,
    )
    create_dev_session_handler = CreateDevSessionHandler(
        unit_of_work_factory,
        module_clock,
        session_tokens,
    )
    revoke_session_handler = RevokeSessionHandler(
        unit_of_work_factory,
        module_clock,
        session_tokens,
    )

    router = APIRouter()
    router.include_router(create_auth_router(
        config=AuthRouterConfig(
            cookie_name=auth_cookie_name,
            cookie_secure=auth_cookie_secure,
            cookie_samesite=auth_cookie_samesite,
            dev_login_enabled=auth_dev_login_enabled,
            session_ttl_seconds=auth_session_ttl_seconds,
            oidc_enabled=auth_oidc_enabled,
            bootstrap_token=auth_bootstrap_token,
        ),
        bootstrap_first_admin_handler=bootstrap_first_admin_handler,
        create_dev_session_handler=create_dev_session_handler,
        revoke_session_handler=revoke_session_handler,
        request_authenticator=request_authenticator,
    ))
    router.include_router(create_identity_router(
        create_user_handler=create_user_handler,
        create_team_handler=create_team_handler,
        add_team_member_handler=add_team_member_handler,
        request_authenticator=request_authenticator,
    ))

    return IdentityModule(
        router=router,
        identity_access=identity_access,
        request_authenticator=request_authenticator,
    )
