from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.tools.domain.repositories import ToolDefinitionRepository
from hify.shared.application.uow import UnitOfWork


class ToolsUnitOfWork(UnitOfWork, Protocol):
    tools: ToolDefinitionRepository

    async def __aenter__(self) -> Self: ...


ToolsUnitOfWorkFactory = Callable[[], ToolsUnitOfWork]
