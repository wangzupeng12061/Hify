from __future__ import annotations

from asyncio import CancelledError
from dataclasses import dataclass
import json
from time import monotonic
from typing import Literal, cast
from uuid import UUID

from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.contracts.dto import ConversationMessageInfo
from hify.modules.conversations.contracts.services import ConversationReader
from hify.modules.identity.contracts.dto import ActorContext
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
from hify.modules.runs.application.authorization import require_execute_runs
from hify.modules.runs.application.dto import run_info_from_domain
from hify.modules.runs.application.ports import RunsUnitOfWork, RunsUnitOfWorkFactory
from hify.modules.runs.contracts.dto import RunInfo
from hify.modules.runs.domain.entities import AgentRun, RunStep
from hify.modules.runs.domain.errors import RunNotFoundError, RunStateConflictError
from hify.modules.runs.domain.value_objects import RunEventType, RunStatus, RunStepType
from hify.modules.tools.contracts.dto import ToolExecutionRequest
from hify.modules.tools.contracts.services import ToolExecutor
from hify.shared.domain.clock import Clock
from hify.shared.domain.errors import HifyError
from hify.shared.domain.ids import new_uuid

MAX_TOOL_ITERATIONS = 5


@dataclass(frozen=True, slots=True)
class ExecuteRunCommand:
    run_id: UUID
    actor: ActorContext | None = None
    cancellation: RunCancellationToken | None = None


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


@dataclass(slots=True)
class PendingToolCall:
    tool_call_id: str
    name: str
    arguments_delta: str = ""

    def append_arguments(self, arguments_delta: str) -> None:
        self.arguments_delta += arguments_delta

    def arguments(self) -> dict[str, object]:
        try:
            value = json.loads(self.arguments_delta or "{}")
        except json.JSONDecodeError as exc:
            raise RunStateConflictError("tool call arguments are invalid") from exc
        if not isinstance(value, dict):
            raise RunStateConflictError("tool call arguments must be an object")
        return cast(dict[str, object], value)

    def tool_id(self) -> UUID:
        try:
            return UUID(self.name)
        except ValueError as exc:
            raise RunStateConflictError("tool call name must be a tool id") from exc

    def execution_id(self) -> UUID:
        try:
            return UUID(self.tool_call_id)
        except ValueError as exc:
            raise RunStateConflictError("tool call id must be a uuid") from exc


@dataclass(slots=True)
class ModelStreamResult:
    finish_reason: str | None
    tool_calls: tuple[PendingToolCall, ...]
    output_text: str


class ToolExecutionFailedError(Exception):
    def __init__(self, run: RunInfo) -> None:
        super().__init__("tool execution failed")
        self.run = run


class RunExecutor:
    def __init__(
        self,
        unit_of_work_factory: RunsUnitOfWorkFactory,
        conversation_reader: ConversationReader,
        agent_catalog: AgentCatalog,
        model_gateway: ModelGateway,
        tool_executor: ToolExecutor,
        clock: Clock,
        *,
        run_timeout_seconds: int = 600,
        max_tool_iterations: int = MAX_TOOL_ITERATIONS,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._conversation_reader = conversation_reader
        self._agent_catalog = agent_catalog
        self._model_gateway = model_gateway
        self._tool_executor = tool_executor
        self._clock = clock
        self._run_timeout_seconds = run_timeout_seconds
        self._max_tool_iterations = max_tool_iterations

    async def execute(self, command: ExecuteRunCommand) -> RunInfo:
        cancellation = command.cancellation or RunCancellationToken()
        run, step = await self._mark_run_started(command.run_id, command.actor)
        agent_version = await self._agent_catalog.get_agent_version(
            team_id=run.team_id,
            agent_version_id=run.agent_version_id,
        )
        messages = list(await self._load_model_messages(run))
        context = CallContext(
            run_id=run.id,
            attempt_id=new_uuid(),
            team_id=run.team_id,
            user_id=run.created_by,
            deadline=monotonic() + self._run_timeout_seconds,
            cancellation=cancellation,
        )

        try:
            for iteration_index in range(self._max_tool_iterations + 1):
                request = ModelRequest(
                    model_id=agent_version.provider_model_id,
                    messages=tuple(messages),
                    system_prompt=agent_version.system_prompt,
                )
                stream_result = await self._stream_model_request(run.id, request, context, cancellation)
                if stream_result.finish_reason != "tool_calls" or not stream_result.tool_calls:
                    return await self._mark_run_succeeded(run.id, step.id)

                if iteration_index >= self._max_tool_iterations:
                    return await self._mark_run_failed(
                        run.id,
                        step.id,
                        "RUN_TOOL_ITERATION_LIMIT_EXCEEDED",
                        "run exceeded maximum tool iterations",
                    )
                await self._mark_step_succeeded(run.id, step.id)
                if stream_result.output_text:
                    messages.append(ModelMessage(role="assistant", content=stream_result.output_text))
                tool_messages = await self._execute_tool_calls(run.id, run.team_id, stream_result.tool_calls)
                messages.extend(tool_messages)
                step = await self._create_step(
                    run.id,
                    RunStepType.LLM_CALL,
                    "Model call",
                    {"iteration": iteration_index + 2},
                )
        except CancelledError:
            cancellation.cancel()
            await self._mark_run_cancelled(run.id, step.id)
            raise
        except ProviderStreamInterruptedError as exc:
            return await self._mark_run_interrupted(run.id, step.id, exc)
        except ProviderCancelledError:
            return await self._mark_run_cancelled(run.id, step.id)
        except ProviderRuntimeError as exc:
            return await self._mark_run_failed(run.id, step.id, exc.code, exc.message)
        except ToolExecutionFailedError as exc:
            return exc.run
        except Exception:
            return await self._mark_run_failed(
                run.id,
                step.id,
                "RUN_EXECUTION_ERROR",
                "run execution failed",
            )

        return await self._mark_run_failed(
            run.id,
            step.id,
            "RUN_TOOL_ITERATION_LIMIT_EXCEEDED",
            "run exceeded maximum tool iterations",
        )

    async def prepare_execution(self, command: ExecuteRunCommand) -> RunInfo:
        if command.actor is not None:
            require_execute_runs(command.actor)

        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(command.run_id)
        if run is None or (
            command.actor is not None and run.team_id != command.actor.team_id
        ):
            raise RunNotFoundError("run was not found")
        if run.status is not RunStatus.QUEUED:
            raise RunStateConflictError("only queued runs can be executed")
        return run_info_from_domain(run)

    async def _mark_run_started(
        self,
        run_id: UUID,
        actor: ActorContext | None,
    ) -> tuple[AgentRun, RunStep]:
        if actor is not None:
            require_execute_runs(actor)

        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await unit_of_work.runs.get_by_id(run_id)
            if run is None or (actor is not None and run.team_id != actor.team_id):
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

    async def _stream_model_request(
        self,
        run_id: UUID,
        request: ModelRequest,
        context: CallContext,
        cancellation: RunCancellationToken,
    ) -> ModelStreamResult:
        tool_calls: dict[str, PendingToolCall] = {}
        output_text_parts: list[str] = []
        finish_reason: str | None = None

        async for chunk in self._model_gateway.stream(request, context):
            cancellation.raise_if_cancelled()
            await self._record_chunk(run_id, chunk)
            if isinstance(chunk, TextDeltaChunk):
                output_text_parts.append(chunk.text)
            elif isinstance(chunk, ToolCallDeltaChunk):
                tool_call = tool_calls.get(chunk.tool_call_id)
                if tool_call is None:
                    tool_call = PendingToolCall(tool_call_id=chunk.tool_call_id, name=chunk.name)
                    tool_calls[chunk.tool_call_id] = tool_call
                tool_call.append_arguments(chunk.arguments_delta)
            elif isinstance(chunk, DoneChunk):
                finish_reason = chunk.finish_reason

        return ModelStreamResult(
            finish_reason=finish_reason,
            tool_calls=tuple(tool_calls.values()),
            output_text="".join(output_text_parts),
        )

    async def _execute_tool_calls(
        self,
        run_id: UUID,
        team_id: UUID,
        tool_calls: tuple[PendingToolCall, ...],
    ) -> list[ModelMessage]:
        messages: list[ModelMessage] = []
        for tool_call in tool_calls:
            step = await self._create_step(
                run_id,
                RunStepType.TOOL_CALL,
                "Tool call",
                {"tool_call_id": tool_call.tool_call_id, "tool_id": tool_call.name},
            )
            try:
                result = await self._tool_executor.execute_tool(
                    ToolExecutionRequest(
                        team_id=team_id,
                        tool_id=tool_call.tool_id(),
                        tool_call_id=tool_call.execution_id(),
                        arguments=tool_call.arguments(),
                    )
                )
            except HifyError as exc:
                run = await self._mark_run_failed(run_id, step.id, exc.code, exc.message)
                raise ToolExecutionFailedError(run) from exc

            await self._record_tool_result(run_id, step.id, tool_call, result.content)
            messages.append(ModelMessage(role="tool", content=result.content))
        return messages

    async def _create_step(
        self,
        run_id: UUID,
        step_type: RunStepType,
        name: str | None,
        payload: dict[str, object],
    ) -> RunStep:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            step = run.create_step(step_type=step_type, name=name, now=now)
            step_started_event = run.create_event(
                event_type=RunEventType.STEP_STARTED,
                payload={"step_id": str(step.id), "step_type": step.step_type.value, **payload},
                now=now,
            )
            await unit_of_work.runs.save(run)
            await unit_of_work.steps.add(step)
            await unit_of_work.events.add(step_started_event)
            await unit_of_work.commit()
        return step

    async def _mark_step_succeeded(self, run_id: UUID, step_id: UUID) -> None:
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
            await unit_of_work.steps.save(step)
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(step_succeeded_event)
            await unit_of_work.commit()

    async def _record_tool_result(
        self,
        run_id: UUID,
        step_id: UUID,
        tool_call: PendingToolCall,
        content: str,
    ) -> None:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            step = await _require_step(unit_of_work, step_id)
            result_event = run.create_event(
                event_type=RunEventType.DIAGNOSTIC,
                payload={
                    "chunk_type": "tool_result",
                    "step_id": str(step.id),
                    "tool_call_id": tool_call.tool_call_id,
                    "tool_id": tool_call.name,
                    "content": content,
                },
                now=now,
            )
            step.mark_succeeded(now)
            step_succeeded_event = run.create_event(
                event_type=RunEventType.STEP_SUCCEEDED,
                payload={"step_id": str(step.id)},
                now=now,
            )
            await unit_of_work.steps.save(step)
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(result_event)
            await unit_of_work.events.add(step_succeeded_event)
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
