from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.application.authorization import require_execute_conversations
from hify.modules.conversations.application.dto import conversation_info_from_domain
from hify.modules.conversations.application.ports import ConversationsUnitOfWorkFactory
from hify.modules.conversations.contracts.dto import ConversationInfo
from hify.modules.conversations.domain.entities import Conversation
from hify.modules.identity.contracts.dto import ActorContext
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateConversationCommand:
    actor: ActorContext
    agent_id: UUID
    title: str | None


class CreateConversationHandler:
    def __init__(
        self,
        unit_of_work_factory: ConversationsUnitOfWorkFactory,
        agent_catalog: AgentCatalog,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._agent_catalog = agent_catalog
        self._clock = clock

    async def handle(self, command: CreateConversationCommand) -> ConversationInfo:
        require_execute_conversations(command.actor)
        await self._agent_catalog.get_latest_published_version(
            team_id=command.actor.team_id,
            agent_id=command.agent_id,
        )
        now = self._clock.now()
        conversation = Conversation.create(
            team_id=command.actor.team_id,
            agent_id=command.agent_id,
            title=command.title,
            created_by=command.actor.user_id,
            now=now,
        )
        async with self._unit_of_work_factory() as unit_of_work:
            await unit_of_work.conversations.add(conversation)
            await unit_of_work.commit()
        return conversation_info_from_domain(conversation)
