from __future__ import annotations

from hify.shared.domain.errors import HifyError


class UsageContractError(HifyError):
    code = "USAGE_CONTRACT_ERROR"
