from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, Self

from hify.modules.agents.domain.repositories import AgentRepository, AgentVersionRepository
from hify.shared.application.uow import UnitOfWork


class AgentsUnitOfWork(UnitOfWork, Protocol):
    agents: AgentRepository
    versions: AgentVersionRepository

    async def __aenter__(self) -> Self: ...


AgentsUnitOfWorkFactory = Callable[[], AgentsUnitOfWork]
