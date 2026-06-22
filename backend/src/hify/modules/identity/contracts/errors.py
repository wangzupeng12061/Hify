from __future__ import annotations


class IdentityContractError(Exception):
    error_code = "IDENTITY_CONTRACT_ERROR"


class IdentityAccessDeniedContractError(IdentityContractError):
    error_code = "IDENTITY_ACCESS_DENIED"
