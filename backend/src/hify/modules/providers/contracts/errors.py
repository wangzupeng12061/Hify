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


class ProviderRuntimeError(ProviderContractError):
    code = "PROVIDER_RUNTIME_ERROR"


class ProviderAuthenticationError(ProviderRuntimeError):
    code = "PROVIDER_AUTHENTICATION_ERROR"


class ProviderPermissionError(ProviderRuntimeError):
    code = "PROVIDER_PERMISSION_ERROR"


class ProviderBadRequestError(ProviderRuntimeError):
    code = "PROVIDER_BAD_REQUEST_ERROR"


class ProviderContextLimitError(ProviderRuntimeError):
    code = "PROVIDER_CONTEXT_LIMIT_ERROR"


class ProviderContentPolicyError(ProviderRuntimeError):
    code = "PROVIDER_CONTENT_POLICY_ERROR"


class ProviderRateLimitError(ProviderRuntimeError):
    code = "PROVIDER_RATE_LIMIT_ERROR"

    def __init__(self, message: str, *, retry_after_seconds: float | None = None) -> None:
        metadata: dict[str, object] = {}
        if retry_after_seconds is not None:
            metadata["retry_after_seconds"] = retry_after_seconds
        super().__init__(message, metadata=metadata or None)
        self.retry_after_seconds = retry_after_seconds


class ProviderTimeoutError(ProviderRuntimeError):
    code = "PROVIDER_TIMEOUT_ERROR"

    def __init__(self, message: str, *, timeout_stage: str) -> None:
        super().__init__(message, metadata={"timeout_stage": timeout_stage})
        self.timeout_stage = timeout_stage


class ProviderUnavailableError(ProviderRuntimeError):
    code = "PROVIDER_UNAVAILABLE_ERROR"


class ProviderStreamInterruptedError(ProviderRuntimeError):
    code = "PROVIDER_STREAM_INTERRUPTED_ERROR"


class ProviderCancelledError(ProviderRuntimeError):
    code = "PROVIDER_CANCELLED_ERROR"
