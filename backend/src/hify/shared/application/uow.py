from __future__ import annotations

from types import TracebackType
from typing import Protocol, Self

from hify.shared.application.events import OutboxMessage


class UnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TransactionalOutbox(Protocol):
    async def add_outbox_message(self, message: OutboxMessage) -> None: ...
