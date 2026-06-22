from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.workflows.domain.repositories import (
    WorkflowRepository,
    WorkflowVersionRepository,
)
from hify.shared.application.uow import UnitOfWork


class WorkflowsUnitOfWork(UnitOfWork, Protocol):
    workflows: WorkflowRepository
    versions: WorkflowVersionRepository

    async def __aenter__(self) -> Self: ...


WorkflowsUnitOfWorkFactory = Callable[[], WorkflowsUnitOfWork]
