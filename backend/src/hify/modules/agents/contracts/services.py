from __future__ import annotations

from typing import Protocol
from uuid import UUID

from hify.modules.agents.contracts.dto import AgentVersionInfo


class AgentCatalog(Protocol):
    async def get_latest_published_version(
        self,
        *,
        team_id: UUID,
        agent_id: UUID,
    ) -> AgentVersionInfo: ...

    async def get_agent_version(
        self,
        *,
        team_id: UUID,
        agent_version_id: UUID,
    ) -> AgentVersionInfo: ...
