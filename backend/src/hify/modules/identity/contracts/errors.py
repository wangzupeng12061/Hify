from __future__ import annotations

from hify.shared.domain.errors import HifyError, PermissionDeniedError


class IdentityContractError(HifyError):
    code = "IDENTITY_CONTRACT_ERROR"


class IdentityAccessDeniedContractError(PermissionDeniedError):
    code = "IDENTITY_ACCESS_DENIED"
