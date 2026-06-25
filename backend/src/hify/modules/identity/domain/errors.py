from __future__ import annotations

from hify.shared.domain.errors import (
    ConflictError,
    HifyError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class IdentityError(HifyError):
    code = "IDENTITY_ERROR"


class IdentityAuthenticationError(IdentityError):
    code = "IDENTITY_AUTHENTICATION_REQUIRED"


class IdentityAuthProviderNotConfiguredError(IdentityError):
    code = "IDENTITY_AUTH_PROVIDER_NOT_CONFIGURED"


class IdentityValidationError(ValidationError):
    code = "IDENTITY_VALIDATION_ERROR"


class UserNotFoundError(NotFoundError):
    code = "IDENTITY_USER_NOT_FOUND"


class TeamNotFoundError(NotFoundError):
    code = "IDENTITY_TEAM_NOT_FOUND"


class MembershipNotFoundError(NotFoundError):
    code = "IDENTITY_MEMBERSHIP_NOT_FOUND"


class UserEmailAlreadyExistsError(ConflictError):
    code = "IDENTITY_USER_EMAIL_ALREADY_EXISTS"


class TeamNameAlreadyExistsError(ConflictError):
    code = "IDENTITY_TEAM_NAME_ALREADY_EXISTS"


class MembershipAlreadyExistsError(ConflictError):
    code = "IDENTITY_MEMBERSHIP_ALREADY_EXISTS"


class FirstAdminAlreadyBootstrappedError(ConflictError):
    code = "IDENTITY_FIRST_ADMIN_ALREADY_BOOTSTRAPPED"


class IdentityPermissionDeniedError(PermissionDeniedError):
    code = "IDENTITY_PERMISSION_DENIED"
