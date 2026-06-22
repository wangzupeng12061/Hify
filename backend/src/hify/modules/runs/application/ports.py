from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.runs.domain.repositories import (
    RunEventRepository,
    RunRepository,
    RunStepRepository,
)
from hify.shared.application.uow import UnitOfWork


class RunsUnitOfWork(UnitOfWork, Protocol):
    runs: RunRepository
    steps: RunStepRepository
    events: RunEventRepository

    async def __aenter__(self) -> Self: ...


RunsUnitOfWorkFactory = Callable[[], RunsUnitOfWork]
