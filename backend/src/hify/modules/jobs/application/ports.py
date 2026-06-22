from __future__ import annotations

from types import TracebackType
from typing import Protocol

from hify.modules.jobs.domain.repositories import JobRepository


class JobsUnitOfWork(Protocol):
    jobs: JobRepository

    async def __aenter__(self) -> JobsUnitOfWork: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


class JobsUnitOfWorkFactory(Protocol):
    def __call__(self) -> JobsUnitOfWork: ...
