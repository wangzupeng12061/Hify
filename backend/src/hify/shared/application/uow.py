from __future__ import annotations

from typing import Protocol, Self

from hify.shared.application.events import OutboxMessage


class UnitOfWork(Protocol):
    async def __aenter__(self) -> Self: ...

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class TransactionalOutbox(Protocol):
    async def add_outbox_message(self, message: OutboxMessage) -> None: ...
