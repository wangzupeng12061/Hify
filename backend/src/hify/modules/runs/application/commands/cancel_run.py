from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.runs.application.authorization import require_execute_runs
from hify.modules.runs.application.dto import run_info_from_domain
from hify.modules.runs.application.ports import RunsUnitOfWorkFactory
from hify.modules.runs.contracts.dto import RunInfo
from hify.modules.runs.domain.errors import RunNotFoundError
from hify.modules.runs.domain.value_objects import RunEventType
from hify.shared.domain.clock import Clock


@dataclass(frozen=True, slots=True)
class CancelRunCommand:
    actor: ActorContext
    run_id: UUID


class CancelRunHandler:
    def __init__(
        self,
        unit_of_work_factory: RunsUnitOfWorkFactory,
        clock: Clock,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._clock = clock

    async def handle(self, command: CancelRunCommand) -> RunInfo:
        require_execute_runs(command.actor)
        now = self._clock.now()

        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(command.run_id)
            if run is None or run.team_id != command.actor.team_id:
                raise RunNotFoundError("run was not found")
            run.cancel(now)
            event = run.create_event(
                event_type=RunEventType.RUN_CANCELLED,
                payload={"run_id": str(run.id)},
                now=now,
            )
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(event)
            await unit_of_work.commit()

        return run_info_from_domain(run)
