from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError, NotFoundError, ValidationError


class ProviderContractError(HifyError):
    code = "PROVIDER_CONTRACT_ERROR"


class ProviderContractValidationError(ValidationError):
    code = "PROVIDER_CONTRACT_VALIDATION_ERROR"


class ProviderContractNotFoundError(NotFoundError):
    code = "PROVIDER_CONTRACT_NOT_FOUND"


class ProviderContractConflictError(ConflictError):
    code = "PROVIDER_CONTRACT_CONFLICT"
