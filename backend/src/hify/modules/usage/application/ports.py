from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.usage.domain.repositories import UsageRecordRepository
from hify.shared.application.uow import UnitOfWork


class UsageUnitOfWork(UnitOfWork, Protocol):
    records: UsageRecordRepository

    async def __aenter__(self) -> Self: ...


UsageUnitOfWorkFactory = Callable[[], UsageUnitOfWork]
