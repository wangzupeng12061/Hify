from __future__ import annotations

from dataclasses import dataclass
from time import monotonic
from typing import Literal, cast
from uuid import UUID

from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.contracts.dto import ConversationMessageInfo
from hify.modules.conversations.contracts.services import ConversationReader
from hify.modules.providers.contracts.dto import (
    CallContext,
    DoneChunk,
    ErrorChunk,
    ModelChunk,
    ModelMessage,
    ModelRequest,
    ReasoningDeltaChunk,
    TextDeltaChunk,
    ToolCallDeltaChunk,
    UsageChunk,
)
from hify.modules.providers.contracts.errors import (
    ProviderCancelledError,
    ProviderRuntimeError,
    ProviderStreamInterruptedError,
)
from hify.modules.providers.contracts.services import ModelGateway
from hify.modules.runs.application.dto import run_info_from_domain
from hify.modules.runs.application.ports import RunsUnitOfWork, RunsUnitOfWorkFactory
from hify.modules.runs.contracts.dto import RunInfo
from hify.modules.runs.domain.entities import AgentRun, RunStep
from hify.modules.runs.domain.errors import RunNotFoundError
from hify.modules.runs.domain.value_objects import RunEventType, RunStepType
from hify.shared.domain.clock import Clock
from hify.shared.domain.ids import new_uuid


@dataclass(frozen=True, slots=True)
class ExecuteRunCommand:
    run_id: UUID


class RunCancellationToken:
    def __init__(self) -> None:
        self._is_cancelled = False

    def cancel(self) -> None:
        self._is_cancelled = True

    def is_cancelled(self) -> bool:
        return self._is_cancelled

    def raise_if_cancelled(self) -> None:
        if self._is_cancelled:
            raise ProviderCancelledError("run execution was cancelled")


class RunExecutor:
    def __init__(
        self,
        unit_of_work_factory: RunsUnitOfWorkFactory,
        conversation_reader: ConversationReader,
        agent_catalog: AgentCatalog,
        model_gateway: ModelGateway,
        clock: Clock,
        *,
        run_timeout_seconds: int = 600,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._conversation_reader = conversation_reader
        self._agent_catalog = agent_catalog
        self._model_gateway = model_gateway
        self._clock = clock
        self._run_timeout_seconds = run_timeout_seconds

    async def execute(self, command: ExecuteRunCommand) -> RunInfo:
        run, step = await self._mark_run_started(command.run_id)
        agent_version = await self._agent_catalog.get_agent_version(
            team_id=run.team_id,
            agent_version_id=run.agent_version_id,
        )
        messages = await self._load_model_messages(run)
        request = ModelRequest(
            model_id=agent_version.provider_model_id,
            messages=messages,
            system_prompt=agent_version.system_prompt,
        )
        context = CallContext(
            run_id=run.id,
            attempt_id=new_uuid(),
            team_id=run.team_id,
            user_id=run.created_by,
            deadline=monotonic() + self._run_timeout_seconds,
            cancellation=RunCancellationToken(),
        )

        try:
            async for chunk in self._model_gateway.stream(request, context):
                await self._record_chunk(run.id, chunk)
        except ProviderStreamInterruptedError as exc:
            return await self._mark_run_interrupted(run.id, step.id, exc)
        except ProviderCancelledError:
            return await self._mark_run_cancelled(run.id, step.id)
        except ProviderRuntimeError as exc:
            return await self._mark_run_failed(run.id, step.id, exc.code, exc.message)
        except Exception:
            return await self._mark_run_failed(
                run.id,
                step.id,
                "RUN_EXECUTION_ERROR",
                "run execution failed",
            )

        return await self._mark_run_succeeded(run.id, step.id)

    async def _mark_run_started(self, run_id: UUID) -> tuple[AgentRun, RunStep]:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(run_id)
            if run is None:
                raise RunNotFoundError("run was not found")
            run.mark_running(now)
            run_started_event = run.create_event(
                event_type=RunEventType.RUN_STARTED,
                payload={"run_id": str(run.id)},
                now=now,
            )
            step = run.create_step(
                step_type=RunStepType.LLM_CALL,
                name="Model call",
                now=now,
            )
            step_started_event = run.create_event(
                event_type=RunEventType.STEP_STARTED,
                payload={"step_id": str(step.id), "step_type": step.step_type.value},
                now=now,
            )
            await unit_of_work.runs.save(run)
            await unit_of_work.steps.add(step)
            await unit_of_work.events.add(run_started_event)
            await unit_of_work.events.add(step_started_event)
            await unit_of_work.commit()
        return run, step

    async def _load_model_messages(self, run: AgentRun) -> tuple[ModelMessage, ...]:
        page = await self._conversation_reader.list_messages(
            team_id=run.team_id,
            conversation_id=run.conversation_id,
            cursor=None,
            limit=100,
        )
        return tuple(_model_message_from_conversation(message) for message in page.items)

    async def _record_chunk(self, run_id: UUID, chunk: ModelChunk) -> None:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(run_id)
            if run is None:
                raise RunNotFoundError("run was not found")
            event = run.create_event(
                event_type=_event_type_for_chunk(chunk),
                payload=_payload_for_chunk(chunk),
                now=now,
            )
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(event)
            await unit_of_work.commit()

    async def _mark_run_succeeded(self, run_id: UUID, step_id: UUID) -> RunInfo:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            step = await _require_step(unit_of_work, step_id)
            step.mark_succeeded(now)
            step_succeeded_event = run.create_event(
                event_type=RunEventType.STEP_SUCCEEDED,
                payload={"step_id": str(step.id)},
                now=now,
            )
            run.mark_succeeded(now)
            run_succeeded_event = run.create_event(
                event_type=RunEventType.RUN_SUCCEEDED,
                payload={"run_id": str(run.id)},
                now=now,
            )
            await unit_of_work.steps.save(step)
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(step_succeeded_event)
            await unit_of_work.events.add(run_succeeded_event)
            await unit_of_work.commit()
        return run_info_from_domain(run)

    async def _mark_run_failed(
        self,
        run_id: UUID,
        step_id: UUID,
        error_code: str,
        error_message: str | None,
    ) -> RunInfo:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            step = await _require_step(unit_of_work, step_id)
            step.mark_failed(error_code=error_code, error_message=error_message, now=now)
            step_failed_event = run.create_event(
                event_type=RunEventType.STEP_FAILED,
                payload={"step_id": str(step.id), "error_code": error_code},
                now=now,
            )
            run.mark_failed(error_code=error_code, error_message=error_message, now=now)
            run_failed_event = run.create_event(
                event_type=RunEventType.RUN_FAILED,
                payload={"run_id": str(run.id), "error_code": error_code},
                now=now,
            )
            await unit_of_work.steps.save(step)
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(step_failed_event)
            await unit_of_work.events.add(run_failed_event)
            await unit_of_work.commit()
        return run_info_from_domain(run)

    async def _mark_run_interrupted(
        self,
        run_id: UUID,
        step_id: UUID,
        error: ProviderStreamInterruptedError,
    ) -> RunInfo:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            step = await _require_step(unit_of_work, step_id)
            step.mark_failed(error_code=error.code, error_message=error.message, now=now)
            step_failed_event = run.create_event(
                event_type=RunEventType.STEP_FAILED,
                payload={"step_id": str(step.id), "error_code": error.code},
                now=now,
            )
            run.mark_interrupted(error_code=error.code, error_message=error.message, now=now)
            run_interrupted_event = run.create_event(
                event_type=RunEventType.RUN_INTERRUPTED,
                payload={"run_id": str(run.id), "error_code": error.code},
                now=now,
            )
            await unit_of_work.steps.save(step)
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(step_failed_event)
            await unit_of_work.events.add(run_interrupted_event)
            await unit_of_work.commit()
        return run_info_from_domain(run)

    async def _mark_run_cancelled(self, run_id: UUID, step_id: UUID) -> RunInfo:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            step = await _require_step(unit_of_work, step_id)
            step.cancel(now)
            run.cancel(now)
            run_cancelled_event = run.create_event(
                event_type=RunEventType.RUN_CANCELLED,
                payload={"run_id": str(run.id)},
                now=now,
            )
            await unit_of_work.steps.save(step)
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(run_cancelled_event)
            await unit_of_work.commit()
        return run_info_from_domain(run)


def _model_message_from_conversation(message: ConversationMessageInfo) -> ModelMessage:
    role = message.role
    if role not in {"system", "user", "assistant", "tool"}:
        role = "user"
    typed_role = cast(Literal["system", "user", "assistant", "tool"], role)
    return ModelMessage(role=typed_role, content=message.content)


def _event_type_for_chunk(chunk: ModelChunk) -> RunEventType:
    if isinstance(chunk, TextDeltaChunk):
        return RunEventType.OUTPUT_TEXT_DELTA
    return RunEventType.DIAGNOSTIC


def _payload_for_chunk(chunk: ModelChunk) -> dict[str, object]:
    if isinstance(chunk, TextDeltaChunk):
        return {"text": chunk.text}
    if isinstance(chunk, ReasoningDeltaChunk):
        return {"chunk_type": chunk.chunk_type, "text": chunk.text}
    if isinstance(chunk, ToolCallDeltaChunk):
        return {
            "chunk_type": chunk.chunk_type,
            "tool_call_id": chunk.tool_call_id,
            "name": chunk.name,
            "arguments_delta": chunk.arguments_delta,
        }
    if isinstance(chunk, UsageChunk):
        return {
            "chunk_type": chunk.chunk_type,
            "input_tokens": chunk.usage.input_tokens,
            "output_tokens": chunk.usage.output_tokens,
            "total_tokens": chunk.usage.total_tokens,
        }
    if isinstance(chunk, DoneChunk):
        return {"chunk_type": chunk.chunk_type, "finish_reason": chunk.finish_reason}
    if isinstance(chunk, ErrorChunk):
        return {
            "chunk_type": chunk.chunk_type,
            "error_code": chunk.error_code,
            "message": chunk.message,
        }
    return {"chunk_type": "unknown"}


async def _require_run(unit_of_work: RunsUnitOfWork, run_id: UUID) -> AgentRun:
    run = await unit_of_work.runs.get_by_id(run_id)
    if run is None:
        raise RunNotFoundError("run was not found")
    return run


async def _require_step(unit_of_work: RunsUnitOfWork, step_id: UUID) -> RunStep:
    step = await unit_of_work.steps.get_by_id(step_id)
    if step is None:
        raise RunNotFoundError("run step was not found")
    return step
