from __future__ import annotations

from types import TracebackType
from typing import Self

from hify.shared.application.uow import UnitOfWork


class ExampleUnitOfWork:
    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None

    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


def test_typical_async_context_manager_satisfies_unit_of_work_protocol() -> None:
    unit_of_work: UnitOfWork = ExampleUnitOfWork()

    assert isinstance(unit_of_work, ExampleUnitOfWork)
