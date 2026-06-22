from __future__ import annotations

from hify.shared.domain.errors import NotFoundError, PermissionDeniedError, ValidationError


class UsageValidationError(ValidationError):
    code = "USAGE_VALIDATION_ERROR"


class UsageNotFoundError(NotFoundError):
    code = "USAGE_NOT_FOUND"


class UsagePermissionDeniedError(PermissionDeniedError):
    code = "USAGE_PERMISSION_DENIED"
