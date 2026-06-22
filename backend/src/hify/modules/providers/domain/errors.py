from __future__ import annotations

from hify.shared.domain.errors import (
    ConflictError,
    HifyError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


class ProviderError(HifyError):
    code = "PROVIDER_ERROR"


class ProviderValidationError(ValidationError):
    code = "PROVIDER_VALIDATION_ERROR"


class ProviderNotFoundError(NotFoundError):
    code = "PROVIDER_NOT_FOUND"


class ProviderAlreadyExistsError(ConflictError):
    code = "PROVIDER_ALREADY_EXISTS"


class ProviderModelNotFoundError(NotFoundError):
    code = "PROVIDER_MODEL_NOT_FOUND"


class ProviderModelAlreadyExistsError(ConflictError):
    code = "PROVIDER_MODEL_ALREADY_EXISTS"


class ProviderPermissionDeniedError(PermissionDeniedError):
    code = "PROVIDER_PERMISSION_DENIED"
