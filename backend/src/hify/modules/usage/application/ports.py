from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.usage.domain.repositories import UsageQuotaRepository, UsageRecordRepository
from hify.shared.application.uow import UnitOfWork


class UsageUnitOfWork(UnitOfWork, Protocol):
    records: UsageRecordRepository
    quotas: UsageQuotaRepository

    async def __aenter__(self) -> Self: ...


UsageUnitOfWorkFactory = Callable[[], UsageUnitOfWork]
