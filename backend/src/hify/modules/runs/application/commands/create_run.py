from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.contracts.services import ConversationReader
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.application.authorization import require_execute_runs
from hify.modules.runs.application.dto import run_info_from_domain
from hify.modules.runs.application.ports import RunsUnitOfWorkFactory
from hify.modules.runs.contracts.dto import RunInfo
from hify.modules.runs.domain.entities import AgentRun
from hify.modules.runs.domain.value_objects import RunEventType, normalize_idempotency_key
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CreateRunCommand:
    actor: ActorContext
    conversation_id: UUID
    idempotency_key: str


class CreateRunHandler:
    def __init__(
        self,
        unit_of_work_factory: RunsUnitOfWorkFactory,
        conversation_reader: ConversationReader,
        agent_catalog: AgentCatalog,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._conversation_reader = conversation_reader
        self._agent_catalog = agent_catalog
        self._clock = clock

    async def handle(self, command: CreateRunCommand) -> RunInfo:
        require_execute_runs(command.actor)
        idempotency_key = normalize_idempotency_key(command.idempotency_key)
        conversation = await self._conversation_reader.get_conversation(
            team_id=command.actor.team_id,
            conversation_id=command.conversation_id,
        )
        agent_version = await self._agent_catalog.get_latest_published_version(
            team_id=command.actor.team_id,
            agent_id=conversation.agent_id,
        )
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            existing_run = await unit_of_work.runs.get_by_idempotency_key(
                team_id=command.actor.team_id,
                conversation_id=command.conversation_id,
                idempotency_key=idempotency_key,
            )
            if existing_run is not None:
                return run_info_from_domain(existing_run)

            run = AgentRun.create(
                team_id=command.actor.team_id,
                conversation_id=conversation.id,
                agent_id=conversation.agent_id,
                agent_version_id=agent_version.id,
                idempotency_key=idempotency_key,
                created_by=command.actor.user_id,
                now=now,
            )
            event = run.create_event(
                event_type=RunEventType.RUN_CREATED,
                payload={
                    "conversation_id": str(conversation.id),
                    "agent_id": str(conversation.agent_id),
                    "agent_version_id": str(agent_version.id),
                },
                now=now,
            )
            await unit_of_work.runs.add(run)
            await unit_of_work.events.add(event)
            await unit_of_work.commit()

        return run_info_from_domain(run)
