from __future__ import annotations

from asyncio import CancelledError
from dataclasses import dataclass
from decimal import Decimal
import json
from time import monotonic
from typing import Literal, Mapping, cast
from uuid import UUID

from hify.modules.agents.contracts.dto import AgentVersionInfo
from hify.modules.agents.contracts.services import AgentCatalog
from hify.modules.conversations.contracts.dto import ConversationMessageInfo
from hify.modules.conversations.contracts.services import ConversationReader, ConversationWriter
from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.knowledge.contracts.dto import RetrievedChunk
from hify.modules.knowledge.contracts.services import KnowledgeRetriever
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
from hify.modules.tools.contracts.dto import ToolExecutionRequest, ToolInfo
from hify.modules.tools.contracts.services import ToolCatalog, ToolExecutor
from hify.modules.usage.contracts.services import UsageRecorder
from hify.shared.domain.clock import Clock
from hify.shared.domain.errors import HifyError
from hify.shared.domain.ids import new_uuid

MAX_TOOL_ITERATIONS = 5
WORKFLOW_RUNTIME_UNSUPPORTED_DEFINITION = "WORKFLOW_RUNTIME_UNSUPPORTED_DEFINITION"
MAX_SOURCE_EVENTS_PER_RESULT = 5
MAX_SOURCE_SNIPPET_LENGTH = 500


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


@dataclass(frozen=True, slots=True)
class WorkflowRuntimeNode:
    node_id: str
    kind: Literal["start", "llm", "tool", "end"]
    config: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class SourceReference:
    source_type: str
    title: str
    url: str | None
    snippet: str | None
    provider: str | None


class ToolExecutionFailedError(Exception):
    def __init__(self, run: RunInfo) -> None:
        super().__init__("tool execution failed")
        self.run = run


class RetrievalFailedError(Exception):
    def __init__(self, run: RunInfo) -> None:
        super().__init__("knowledge retrieval failed")
        self.run = run


class WorkflowRuntimeUnsupportedDefinitionError(Exception):
    pass


class RunExecutor:
    def __init__(
        self,
        unit_of_work_factory: RunsUnitOfWorkFactory,
        conversation_reader: ConversationReader,
        conversation_writer: ConversationWriter,
        agent_catalog: AgentCatalog,
        model_gateway: ModelGateway,
        tool_executor: ToolExecutor,
        knowledge_retriever: KnowledgeRetriever,
        usage_recorder: UsageRecorder,
        clock: Clock,
        *,
        tool_catalog: ToolCatalog | None = None,
        run_timeout_seconds: int = 600,
        max_tool_iterations: int = MAX_TOOL_ITERATIONS,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory
        self._conversation_reader = conversation_reader
        self._conversation_writer = conversation_writer
        self._agent_catalog = agent_catalog
        self._model_gateway = model_gateway
        self._tool_executor = tool_executor
        self._tool_catalog = tool_catalog
        self._knowledge_retriever = knowledge_retriever
        self._usage_recorder = usage_recorder
        self._clock = clock
        self._run_timeout_seconds = run_timeout_seconds
        self._max_tool_iterations = max_tool_iterations

    async def execute(self, command: ExecuteRunCommand) -> RunInfo:
        cancellation = command.cancellation or RunCancellationToken()
        run = await self._mark_run_started(command.run_id, command.actor)
        agent_version = await self._agent_catalog.get_agent_version(
            team_id=run.team_id,
            agent_version_id=run.agent_version_id,
        )
        await self._record_workflow_snapshot(run.id, agent_version)
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
            system_prompt = await self._build_system_prompt(
                run=run,
                agent_version=agent_version,
                messages=tuple(messages),
                context=context,
            )
        except RetrievalFailedError as exc:
            return exc.run

        if agent_version.workflow_definition is not None:
            return await self._execute_workflow(
                run=run,
                agent_version=agent_version,
                messages=tuple(messages),
                system_prompt=system_prompt,
                context=context,
                cancellation=cancellation,
            )

        model_tools = await self._model_tools_for_run(run.team_id, agent_version)
        step = await self._create_step(run.id, RunStepType.LLM_CALL, "Model call", {})
        try:
            for iteration_index in range(self._max_tool_iterations + 1):
                request = ModelRequest(
                    model_id=agent_version.provider_model_id,
                    messages=tuple(messages),
                    system_prompt=system_prompt,
                    tools=model_tools,
                )
                stream_result = await self._stream_model_request(
                    run=run,
                    agent_version=agent_version,
                    step_id=step.id,
                    request=request,
                    context=context,
                    cancellation=cancellation,
                )
                if stream_result.finish_reason != "tool_calls" or not stream_result.tool_calls:
                    return await self._mark_run_succeeded_with_output(
                        run=run,
                        step_id=step.id,
                        output_text=stream_result.output_text,
                    )

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
        except RetrievalFailedError as exc:
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

    async def _execute_workflow(
        self,
        *,
        run: AgentRun,
        agent_version: AgentVersionInfo,
        messages: tuple[ModelMessage, ...],
        system_prompt: str,
        context: CallContext,
        cancellation: RunCancellationToken,
    ) -> RunInfo:
        workflow_step = await self._create_step(
            run.id,
            RunStepType.SYSTEM,
            "Workflow runtime",
            {
                "workflow_version_id": (
                    str(agent_version.workflow_version_id)
                    if agent_version.workflow_version_id is not None
                    else None
                )
            },
        )
        current_step = workflow_step
        try:
            workflow_definition = agent_version.workflow_definition
            if workflow_definition is None:
                raise WorkflowRuntimeUnsupportedDefinitionError("workflow definition is missing")
            workflow_path = _linear_workflow_path(workflow_definition)
            await self._mark_step_succeeded(run.id, workflow_step.id)
            workflow_messages = list(messages)
            last_output_text = ""

            for node in workflow_path:
                if node.kind in {"start", "end"}:
                    continue
                if node.kind == "llm":
                    current_step = await self._create_step(
                        run.id,
                        RunStepType.LLM_CALL,
                        "Workflow LLM node",
                        {"workflow_node_id": node.node_id},
                    )
                    request = ModelRequest(
                        model_id=_workflow_node_uuid_config(node, "provider_model_id"),
                        messages=tuple(workflow_messages),
                        system_prompt=system_prompt,
                    )
                    stream_result = await self._stream_model_request(
                        run=run,
                        agent_version=agent_version,
                        step_id=current_step.id,
                        request=request,
                        context=context,
                        cancellation=cancellation,
                    )
                    if stream_result.tool_calls:
                        return await self._mark_run_failed(
                            run.id,
                            current_step.id,
                            WORKFLOW_RUNTIME_UNSUPPORTED_DEFINITION,
                            "workflow llm nodes must not emit model tool calls",
                        )
                    if stream_result.output_text:
                        last_output_text = stream_result.output_text
                        workflow_messages.append(
                            ModelMessage(role="assistant", content=stream_result.output_text)
                        )
                    await self._mark_step_succeeded(run.id, current_step.id)
                    continue

                current_step = await self._create_step(
                    run.id,
                    RunStepType.TOOL_CALL,
                    "Workflow tool node",
                    {"workflow_node_id": node.node_id},
                )
                tool_message = await self._execute_workflow_tool_node(
                    run_id=run.id,
                    team_id=run.team_id,
                    step_id=current_step.id,
                    node=node,
                )
                workflow_messages.append(tool_message)

            end_step = await self._create_step(
                run.id,
                RunStepType.SYSTEM,
                "Workflow end",
                {},
            )
            return await self._mark_run_succeeded_with_output(
                run=run,
                step_id=end_step.id,
                output_text=last_output_text,
            )
        except WorkflowRuntimeUnsupportedDefinitionError as exc:
            return await self._mark_run_failed(
                run.id,
                current_step.id,
                WORKFLOW_RUNTIME_UNSUPPORTED_DEFINITION,
                str(exc),
            )
        except CancelledError:
            cancellation.cancel()
            await self._mark_run_cancelled(run.id, current_step.id)
            raise
        except ProviderStreamInterruptedError as exc:
            return await self._mark_run_interrupted(run.id, current_step.id, exc)
        except ProviderCancelledError:
            return await self._mark_run_cancelled(run.id, current_step.id)
        except ProviderRuntimeError as exc:
            return await self._mark_run_failed(run.id, current_step.id, exc.code, exc.message)
        except ToolExecutionFailedError as exc:
            return exc.run
        except Exception:
            return await self._mark_run_failed(
                run.id,
                current_step.id,
                "RUN_EXECUTION_ERROR",
                "run execution failed",
            )

    async def _execute_workflow_tool_node(
        self,
        *,
        run_id: UUID,
        team_id: UUID,
        step_id: UUID,
        node: WorkflowRuntimeNode,
    ) -> ModelMessage:
        tool_id = _workflow_node_uuid_config(node, "tool_id")
        arguments = _workflow_tool_arguments(node)
        tool_call = PendingToolCall(
            tool_call_id=str(new_uuid()),
            name=str(tool_id),
            arguments_delta=json.dumps(arguments),
        )
        try:
            result = await self._tool_executor.execute_tool(
                ToolExecutionRequest(
                    team_id=team_id,
                    tool_id=tool_id,
                    tool_call_id=tool_call.execution_id(),
                    arguments=arguments,
                )
            )
        except HifyError as exc:
            run = await self._mark_run_failed(run_id, step_id, exc.code, exc.message)
            raise ToolExecutionFailedError(run) from exc

        await self._record_tool_result(run_id, step_id, tool_call, result)
        return ModelMessage(role="tool", content=result.content)

    async def _build_system_prompt(
        self,
        *,
        run: AgentRun,
        agent_version: AgentVersionInfo,
        messages: tuple[ModelMessage, ...],
        context: CallContext,
    ) -> str:
        system_prompt = agent_version.system_prompt
        knowledge_base_ids = agent_version.knowledge_base_ids
        if not knowledge_base_ids:
            return system_prompt
        query = _last_user_message_content(messages)
        if query is None:
            return system_prompt
        chunks = await self._retrieve_knowledge_context(
            run=run,
            knowledge_base_ids=knowledge_base_ids,
            query=query,
            context=context,
        )
        if not chunks:
            return system_prompt
        return f"{system_prompt}\n\n{_format_retrieved_context(chunks)}"

    async def _retrieve_knowledge_context(
        self,
        *,
        run: AgentRun,
        knowledge_base_ids: tuple[UUID, ...],
        query: str,
        context: CallContext,
    ) -> tuple[RetrievedChunk, ...]:
        step = await self._create_step(
            run.id,
            RunStepType.RETRIEVAL,
            "Knowledge retrieval",
            {"knowledge_base_ids": [str(item) for item in knowledge_base_ids]},
        )
        await self._record_activity_started(
            run.id,
            step.id,
            title="Searching knowledge bases",
            detail=f"Retrieving context from {len(knowledge_base_ids)} knowledge base(s).",
        )
        try:
            chunks = await self._knowledge_retriever.retrieve(
                team_id=run.team_id,
                user_id=run.created_by,
                knowledge_base_ids=knowledge_base_ids,
                query=query,
                limit=5,
                deadline=context.deadline,
            )
        except HifyError as exc:
            failed_run = await self._mark_run_failed(run.id, step.id, exc.code, exc.message)
            raise RetrievalFailedError(failed_run) from exc
        await self._record_retrieval_result(run.id, step.id, chunks)
        return chunks

    async def _record_retrieval_result(
        self,
        run_id: UUID,
        step_id: UUID,
        chunks: tuple[RetrievedChunk, ...],
    ) -> None:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            step = await _require_step(unit_of_work, step_id)
            result_event = run.create_event(
                event_type=RunEventType.DIAGNOSTIC,
                payload={
                    "chunk_type": "retrieval_result",
                    "step_id": str(step.id),
                    "chunk_count": len(chunks),
                    "chunks": [
                        {
                            "chunk_id": str(chunk.chunk_id),
                            "knowledge_base_id": str(chunk.knowledge_base_id),
                            "document_id": str(chunk.document_id),
                            "position": chunk.position,
                            "score": chunk.score,
                        }
                        for chunk in chunks
                    ],
                },
                now=now,
            )
            source_events = [
                run.create_event(
                    event_type=RunEventType.SOURCE_DISCOVERED,
                    payload={
                        "source_type": "knowledge",
                        "title": f"Knowledge chunk {chunk.position + 1}",
                        "url": None,
                        "snippet": _truncate_source_snippet(chunk.content),
                        "provider": "knowledge",
                        "step_id": str(step.id),
                        "chunk_id": str(chunk.chunk_id),
                        "knowledge_base_id": str(chunk.knowledge_base_id),
                        "document_id": str(chunk.document_id),
                        "score": chunk.score,
                    },
                    now=now,
                )
                for chunk in chunks[:MAX_SOURCE_EVENTS_PER_RESULT]
            ]
            activity_completed_event = run.create_event(
                event_type=RunEventType.ACTIVITY_COMPLETED,
                payload={
                    "step_id": str(step.id),
                    "title": "Knowledge context retrieved",
                    "detail": f"Found {len(chunks)} relevant chunk(s).",
                    "status": "completed",
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
            for source_event in source_events:
                await unit_of_work.events.add(source_event)
            await unit_of_work.events.add(activity_completed_event)
            await unit_of_work.events.add(step_succeeded_event)
            await unit_of_work.commit()

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
    ) -> AgentRun:
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
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(run_started_event)
            await unit_of_work.commit()
        return run

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

    async def _record_workflow_snapshot(
        self,
        run_id: UUID,
        agent_version: AgentVersionInfo,
    ) -> None:
        if agent_version.workflow_version_id is None:
            return
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            event = run.create_event(
                event_type=RunEventType.DIAGNOSTIC,
                payload={
                    "chunk_type": "workflow_snapshot",
                    "workflow_id": (
                        str(agent_version.workflow_id)
                        if agent_version.workflow_id is not None
                        else None
                    ),
                    "workflow_version_id": str(agent_version.workflow_version_id),
                    "workflow_version_number": agent_version.workflow_version_number,
                    "workflow_name": agent_version.workflow_name,
                    "workflow_definition": agent_version.workflow_definition or {},
                },
                now=now,
            )
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(event)
            await unit_of_work.commit()

    async def _stream_model_request(
        self,
        *,
        run: AgentRun,
        agent_version: AgentVersionInfo,
        step_id: UUID,
        request: ModelRequest,
        context: CallContext,
        cancellation: RunCancellationToken,
    ) -> ModelStreamResult:
        tool_calls: dict[str, PendingToolCall] = {}
        output_text_parts: list[str] = []
        finish_reason: str | None = None
        usage_chunk_count = 0

        async for chunk in self._model_gateway.stream(request, context):
            cancellation.raise_if_cancelled()
            await self._record_chunk(run.id, chunk)
            if isinstance(chunk, TextDeltaChunk):
                output_text_parts.append(chunk.text)
            elif isinstance(chunk, ToolCallDeltaChunk):
                tool_call = tool_calls.get(chunk.tool_call_id)
                if tool_call is None:
                    tool_call = PendingToolCall(tool_call_id=chunk.tool_call_id, name=chunk.name)
                    tool_calls[chunk.tool_call_id] = tool_call
                tool_call.append_arguments(chunk.arguments_delta)
            elif isinstance(chunk, UsageChunk):
                usage_chunk_count += 1
                await self._record_model_usage(
                    run=run,
                    agent_version=agent_version,
                    step_id=step_id,
                    usage_index=usage_chunk_count,
                    chunk=chunk,
                )
            elif isinstance(chunk, DoneChunk):
                finish_reason = chunk.finish_reason

        return ModelStreamResult(
            finish_reason=finish_reason,
            tool_calls=tuple(tool_calls.values()),
            output_text="".join(output_text_parts),
        )

    async def _model_tools_for_run(
        self,
        team_id: UUID,
        agent_version: AgentVersionInfo,
    ) -> tuple[Mapping[str, object], ...]:
        if not agent_version.supports_tools or self._tool_catalog is None:
            return ()
        tools = await self._tool_catalog.list_tools(team_id=team_id)
        return tuple(_model_tool_from_tool(tool) for tool in tools if tool.status == "active")

    async def _record_model_usage(
        self,
        *,
        run: AgentRun,
        agent_version: AgentVersionInfo,
        step_id: UUID,
        usage_index: int,
        chunk: UsageChunk,
    ) -> None:
        try:
            await self._usage_recorder.record_model_usage(
                team_id=run.team_id,
                user_id=run.created_by,
                run_id=run.id,
                agent_id=run.agent_id,
                agent_version_id=run.agent_version_id,
                provider_model_id=agent_version.provider_model_id,
                provider=agent_version.provider_type,
                model=agent_version.model_name,
                input_tokens=chunk.usage.input_tokens,
                output_tokens=chunk.usage.output_tokens,
                cost_amount=Decimal("0"),
                idempotency_key=f"run:{run.id}:step:{step_id}:usage:{usage_index}",
                occurred_at=self._clock.now(),
            )
        except HifyError as exc:
            await self._record_usage_write_failed(run.id, step_id, exc)

    async def _record_usage_write_failed(
        self,
        run_id: UUID,
        step_id: UUID,
        error: HifyError,
    ) -> None:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            event = run.create_event(
                event_type=RunEventType.DIAGNOSTIC,
                payload={
                    "chunk_type": "usage_write_failed",
                    "step_id": str(step_id),
                    "error_code": error.code,
                    "message": error.message,
                },
                now=now,
            )
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(event)
            await unit_of_work.commit()

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
            await self._record_activity_started(
                run_id,
                step.id,
                title="Calling tool",
                detail=f"Executing tool {tool_call.name}.",
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

            await self._record_tool_result(run_id, step.id, tool_call, result)
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
        result: ToolExecutionResult,
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
                    "content_size": len(result.content),
                },
                now=now,
            )
            source_events = [
                run.create_event(
                    event_type=RunEventType.SOURCE_DISCOVERED,
                    payload={
                        "source_type": source.source_type,
                        "title": source.title,
                        "url": source.url,
                        "snippet": source.snippet,
                        "provider": source.provider,
                        "step_id": str(step.id),
                        "tool_call_id": tool_call.tool_call_id,
                        "tool_id": tool_call.name,
                    },
                    now=now,
                )
                for source in _source_references_from_tool_result(result)
            ]
            activity_completed_event = run.create_event(
                event_type=RunEventType.ACTIVITY_COMPLETED,
                payload={
                    "step_id": str(step.id),
                    "title": "Tool call completed",
                    "detail": f"Tool returned {len(result.content)} characters.",
                    "status": "completed",
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
            for source_event in source_events:
                await unit_of_work.events.add(source_event)
            await unit_of_work.events.add(activity_completed_event)
            await unit_of_work.events.add(step_succeeded_event)
            await unit_of_work.commit()

    async def _record_activity_started(
        self,
        run_id: UUID,
        step_id: UUID,
        *,
        title: str,
        detail: str,
    ) -> None:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            event = run.create_event(
                event_type=RunEventType.ACTIVITY_STARTED,
                payload={
                    "step_id": str(step_id),
                    "title": title,
                    "detail": detail,
                    "status": "started",
                },
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

    async def _mark_run_succeeded_with_output(
        self,
        *,
        run: AgentRun,
        step_id: UUID,
        output_text: str,
    ) -> RunInfo:
        result = await self._mark_run_succeeded(run.id, step_id)
        content = output_text.strip()
        if not content:
            return result

        try:
            await self._conversation_writer.append_assistant_message(
                team_id=run.team_id,
                conversation_id=run.conversation_id,
                content=content,
                source_run_id=run.id,
                created_by=run.created_by,
            )
        except HifyError as exc:
            return await self._record_assistant_output_write_failed(run.id, exc)
        return result

    async def _record_assistant_output_write_failed(
        self,
        run_id: UUID,
        error: HifyError,
    ) -> RunInfo:
        now = self._clock.now()
        async with self._unit_of_work_factory() as unit_of_work:
            run = await _require_run(unit_of_work, run_id)
            event = run.create_event(
                event_type=RunEventType.DIAGNOSTIC,
                payload={
                    "chunk_type": "assistant_output_write_failed",
                    "error_code": error.code,
                    "message": error.message,
                },
                now=now,
            )
            await unit_of_work.runs.save(run)
            await unit_of_work.events.add(event)
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


def _last_user_message_content(messages: tuple[ModelMessage, ...]) -> str | None:
    for message in reversed(messages):
        if message.role == "user" and message.content.strip():
            return message.content
    return None


def _format_retrieved_context(chunks: tuple[RetrievedChunk, ...]) -> str:
    lines = [
        "Use the following retrieved knowledge context when it is relevant. "
        "If the context does not answer the user, say so instead of inventing facts.",
        "",
        "<retrieved_context>",
    ]
    for index, chunk in enumerate(chunks, start=1):
        lines.extend(
            (
                f"<chunk index=\"{index}\" knowledge_base_id=\"{chunk.knowledge_base_id}\" "
                f"document_id=\"{chunk.document_id}\" score=\"{chunk.score:.4f}\">",
                chunk.content,
                "</chunk>",
            )
        )
    lines.append("</retrieved_context>")
    return "\n".join(lines)


def _event_type_for_chunk(chunk: ModelChunk) -> RunEventType:
    if isinstance(chunk, TextDeltaChunk):
        return RunEventType.OUTPUT_TEXT_DELTA
    return RunEventType.DIAGNOSTIC


def _model_tool_from_tool(tool: ToolInfo) -> Mapping[str, object]:
    return {
        "type": "function",
        "function": {
            "name": str(tool.id),
            "description": _model_tool_description(tool),
            "parameters": dict(tool.input_schema),
        },
    }


def _model_tool_description(tool: ToolInfo) -> str:
    target = tool.builtin_name or tool.mcp_tool_name or tool.endpoint_url or tool.tool_kind
    description_parts = [
        f"Use the Hify tool named '{tool.name}'.",
        f"Target: {target}.",
    ]
    if tool.description:
        description_parts.append(tool.description)
    return " ".join(description_parts)[:1000]


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


def _source_references_from_tool_result(
    result: ToolExecutionResult,
) -> tuple[SourceReference, ...]:
    try:
        parsed = json.loads(result.content)
    except json.JSONDecodeError:
        return ()
    if not isinstance(parsed, dict):
        return ()

    raw_results = parsed.get("results")
    if not isinstance(raw_results, list):
        return ()
    provider = _optional_payload_string(result.metadata.get("provider"))
    references: list[SourceReference] = []
    seen_urls: set[str] = set()
    for item in raw_results:
        if len(references) >= MAX_SOURCE_EVENTS_PER_RESULT:
            break
        if not isinstance(item, dict):
            continue
        url = _optional_payload_string(item.get("url"))
        title = _optional_payload_string(item.get("title"))
        snippet = _optional_payload_string(item.get("snippet"))
        if url is None or title is None or url in seen_urls:
            continue
        seen_urls.add(url)
        references.append(
            SourceReference(
                source_type="web",
                title=title[:120],
                url=url,
                snippet=_truncate_source_snippet(snippet),
                provider=provider,
            )
        )
    return tuple(references)


def _truncate_source_snippet(value: object) -> str | None:
    text = _optional_payload_string(value)
    if text is None:
        return None
    if len(text) <= MAX_SOURCE_SNIPPET_LENGTH:
        return text
    return f"{text[: MAX_SOURCE_SNIPPET_LENGTH - 3]}..."


def _optional_payload_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


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


def _linear_workflow_path(definition: Mapping[str, object]) -> tuple[WorkflowRuntimeNode, ...]:
    nodes_value = definition.get("nodes")
    edges_value = definition.get("edges")
    if not isinstance(nodes_value, list) or not isinstance(edges_value, list):
        raise WorkflowRuntimeUnsupportedDefinitionError("workflow definition requires nodes and edges")

    nodes: dict[str, WorkflowRuntimeNode] = {}
    start_node_id: str | None = None
    end_node_id: str | None = None
    for node_value in nodes_value:
        if not isinstance(node_value, dict):
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow nodes must be objects")
        node_id_value = node_value.get("id")
        kind_value = node_value.get("kind")
        config_value = node_value.get("config", {})
        if not isinstance(node_id_value, str) or not node_id_value:
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow nodes require string ids")
        if node_id_value in nodes:
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow node ids must be unique")
        if kind_value not in {"start", "llm", "tool", "end"}:
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow contains unsupported node kind")
        if not isinstance(config_value, dict):
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow node config must be an object")
        typed_kind = cast(Literal["start", "llm", "tool", "end"], kind_value)
        nodes[node_id_value] = WorkflowRuntimeNode(
            node_id=node_id_value,
            kind=typed_kind,
            config=cast(Mapping[str, object], config_value),
        )
        if typed_kind == "start":
            if start_node_id is not None:
                raise WorkflowRuntimeUnsupportedDefinitionError("workflow runtime supports one start node")
            start_node_id = node_id_value
        elif typed_kind == "end":
            if end_node_id is not None:
                raise WorkflowRuntimeUnsupportedDefinitionError("workflow runtime supports one end node")
            end_node_id = node_id_value

    if start_node_id is None or end_node_id is None:
        raise WorkflowRuntimeUnsupportedDefinitionError("workflow requires one start and one end node")

    outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    incoming: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for edge_value in edges_value:
        if not isinstance(edge_value, dict):
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow edges must be objects")
        source_node_id = edge_value.get("source_node_id")
        target_node_id = edge_value.get("target_node_id")
        if not isinstance(source_node_id, str) or not isinstance(target_node_id, str):
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow edges require source and target")
        if source_node_id not in nodes or target_node_id not in nodes:
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow edges must reference known nodes")
        outgoing[source_node_id].append(target_node_id)
        incoming[target_node_id].append(source_node_id)

    for node_id, node in nodes.items():
        if node.kind == "end":
            if outgoing[node_id]:
                raise WorkflowRuntimeUnsupportedDefinitionError("end node must not have outgoing edges")
        elif len(outgoing[node_id]) != 1:
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow runtime supports single-path flows only")
        if node.kind == "start":
            if incoming[node_id]:
                raise WorkflowRuntimeUnsupportedDefinitionError("start node must not have incoming edges")
        elif len(incoming[node_id]) != 1:
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow runtime supports single-path flows only")

    path_ids: list[str] = []
    visited: set[str] = set()
    current_node_id = start_node_id
    while True:
        if current_node_id in visited:
            raise WorkflowRuntimeUnsupportedDefinitionError("workflow runtime does not support cycles")
        visited.add(current_node_id)
        path_ids.append(current_node_id)
        if current_node_id == end_node_id:
            break
        current_node_id = outgoing[current_node_id][0]

    if visited != set(nodes):
        raise WorkflowRuntimeUnsupportedDefinitionError("workflow runtime supports one connected path only")
    path = tuple(nodes[node_id] for node_id in path_ids)
    if not any(node.kind == "llm" for node in path):
        raise WorkflowRuntimeUnsupportedDefinitionError("workflow runtime requires at least one llm node")
    return path


def _workflow_node_uuid_config(node: WorkflowRuntimeNode, field_name: str) -> UUID:
    value = node.config.get(field_name)
    if not isinstance(value, str):
        raise WorkflowRuntimeUnsupportedDefinitionError(
            f"workflow {node.kind} node requires {field_name}"
        )
    try:
        return UUID(value)
    except ValueError as exc:
        raise WorkflowRuntimeUnsupportedDefinitionError(
            f"workflow {node.kind} node {field_name} must be a uuid"
        ) from exc


def _workflow_tool_arguments(node: WorkflowRuntimeNode) -> dict[str, object]:
    value = node.config.get("arguments", {})
    if not isinstance(value, dict):
        raise WorkflowRuntimeUnsupportedDefinitionError("workflow tool arguments must be an object")
    return cast(dict[str, object], value)
