from __future__ import annotations

from hify.shared.domain.errors import ConflictError, HifyError


class UsageContractError(HifyError):
    code = "USAGE_CONTRACT_ERROR"


class UsageQuotaExceededError(ConflictError):
    code = "USAGE_QUOTA_EXCEEDED"
