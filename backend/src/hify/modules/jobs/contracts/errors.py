from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, ValidationError


class JobContractError(HifyError):
    code = "JOB_CONTRACT_ERROR"


class JobContractValidationError(ValidationError):
    code = "JOB_CONTRACT_VALIDATION_ERROR"


class JobContractNotFoundError(NotFoundError):
    code = "JOB_CONTRACT_NOT_FOUND"


class JobContractConflictError(ConflictError):
    code = "JOB_CONTRACT_CONFLICT"
