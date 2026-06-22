from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, ValidationError


class RunContractError(HifyError):
    code = "RUN_CONTRACT_ERROR"


class RunContractValidationError(ValidationError):
    code = "RUN_CONTRACT_VALIDATION_ERROR"


class RunContractNotFoundError(NotFoundError):
    code = "RUN_CONTRACT_NOT_FOUND"


class RunContractConflictError(ConflictError):
    code = "RUN_CONTRACT_CONFLICT"
