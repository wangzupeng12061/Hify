from __future__ import annotations

from datetime import UTC, datetime
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.providers.contracts.dto import ModelInfo
from hify.modules.tools.contracts.dto import ToolInfo
from hify.modules.workflows.application.commands.create_workflow import (
    CreateWorkflowCommand,
    CreateWorkflowHandler,
)
from hify.modules.workflows.application.commands.publish_workflow import (
    PublishWorkflowCommand,
    PublishWorkflowHandler,
)
from hify.modules.workflows.application.commands.update_workflow_draft import (
    UpdateWorkflowDraftCommand,
    UpdateWorkflowDraftHandler,
)
from hify.modules.workflows.application.queries.get_workflow import (
    GetLatestPublishedWorkflowVersionHandler,
    GetWorkflowForActorHandler,
    GetWorkflowForActorQuery,
    GetWorkflowVersionHandler,
    WorkflowCatalogService,
)
from hify.modules.workflows.application.queries.list_workflows import (
    ListWorkflowsForActorHandler,
    ListWorkflowsForActorQuery,
)
from hify.modules.workflows.application.queries.validate_workflow import (
    ValidateWorkflowDraftHandler,
    ValidateWorkflowDraftQuery,
)
from hify.modules.workflows.domain.entities import Workflow, WorkflowVersion
from hify.modules.workflows.domain.errors import (
    WorkflowAlreadyExistsError,
    WorkflowPermissionDeniedError,
)
from hify.modules.workflows.domain.value_objects import default_workflow_definition
from hify.shared.domain.clock import Clock


class FixedClock(Clock):
    def now(self) -> datetime:
        return datetime(2026, 6, 22, tzinfo=UTC)


class FakeModelCatalog:
    def __init__(self, model: ModelInfo) -> None:
        self.model = model
        self.requests: list[UUID] = []

    async def get_model(self, *, team_id: UUID, model_id: UUID) -> ModelInfo:
        assert team_id == self.model.team_id
        assert model_id == self.model.id
        self.requests.append(model_id)
        return self.model

    async def list_models(self, *, team_id: UUID) -> tuple[ModelInfo, ...]:
        assert team_id == self.model.team_id
        return (self.model,)


class FakeToolCatalog:
    def __init__(self, tool: ToolInfo) -> None:
        self.tool = tool
        self.requests: list[UUID] = []

    async def get_tool(self, *, team_id: UUID, tool_id: UUID) -> ToolInfo:
        assert team_id == self.tool.team_id
        assert tool_id == self.tool.id
        self.requests.append(tool_id)
        return self.tool

    async def list_tools(self, *, team_id: UUID) -> tuple[ToolInfo, ...]:
        assert team_id == self.tool.team_id
        return (self.tool,)


class FakeWorkflowRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Workflow] = {}

    async def add(self, workflow: Workflow) -> None:
        self.items[workflow.id] = workflow

    async def save(self, workflow: Workflow) -> None:
        self.items[workflow.id] = workflow

    async def get_by_id(self, workflow_id: UUID) -> Workflow | None:
        return self.items.get(workflow_id)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> Workflow | None:
        for workflow in self.items.values():
            if workflow.team_id == team_id and workflow.name.lower() == name.lower():
                return workflow
        return None

    async def list_by_team(self, *, team_id: UUID) -> tuple[Workflow, ...]:
        return tuple(
            sorted(
                (workflow for workflow in self.items.values() if workflow.team_id == team_id),
                key=lambda workflow: (workflow.status.value, workflow.created_at, workflow.id),
                reverse=True,
            )
        )


class FakeWorkflowVersionRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, WorkflowVersion] = {}

    async def add(self, workflow_version: WorkflowVersion) -> None:
        self.items[workflow_version.id] = workflow_version

    async def get_by_id(self, workflow_version_id: UUID) -> WorkflowVersion | None:
        return self.items.get(workflow_version_id)

    async def get_latest_by_workflow_id(self, workflow_id: UUID) -> WorkflowVersion | None:
        versions = [
            version for version in self.items.values() if version.workflow_id == workflow_id
        ]
        if not versions:
            return None
        return max(versions, key=lambda version: version.version_number)


class FakeWorkflowsUnitOfWork:
    def __init__(self) -> None:
        self.workflows = FakeWorkflowRepository()
        self.versions = FakeWorkflowVersionRepository()
        self.committed = False
        self.rolled_back = False

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if exc_type is not None:
            await self.rollback()

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def actor_with_workflow_permissions() -> ActorContext:
    return ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="admin",
        permissions=("workflows.manage", "workflows.read"),
    )


def active_chat_model(team_id: UUID) -> ModelInfo:
    return ModelInfo(
        id=UUID("00000000-0000-7000-8000-000000000004"),
        team_id=team_id,
        provider_id=UUID("00000000-0000-7000-8000-000000000005"),
        provider_type="openai",
        provider_name="OpenAI",
        model_name="gpt-4.1",
        display_name="GPT 4.1",
        kind="chat",
        status="active",
        context_window_tokens=128000,
        supports_tools=True,
        supports_vision=True,
        supports_structured_output=True,
        price_per_1m_input_tokens=None,
        price_per_1m_output_tokens=None,
    )


def active_tool(team_id: UUID) -> ToolInfo:
    return ToolInfo(
        id=UUID("00000000-0000-7000-8000-000000000006"),
        team_id=team_id,
        name="Search",
        description=None,
        tool_kind="builtin",
        status="active",
        input_schema={"type": "object"},
        builtin_name="web.search",
        endpoint_url=None,
        http_method=None,
        http_headers={},
        mcp_server_id=None,
        mcp_tool_id=None,
        mcp_tool_name=None,
        created_at=datetime(2026, 6, 22, tzinfo=UTC),
        updated_at=datetime(2026, 6, 22, tzinfo=UTC),
    )


def workflow_definition_with_model_and_tool() -> dict[str, object]:
    return {
        "nodes": [
            {"id": "start", "kind": "start", "config": {}},
            {
                "id": "llm",
                "kind": "llm",
                "config": {"provider_model_id": "00000000-0000-7000-8000-000000000004"},
            },
            {
                "id": "tool",
                "kind": "tool",
                "config": {"tool_id": "00000000-0000-7000-8000-000000000006"},
            },
            {"id": "end", "kind": "end", "config": {}},
        ],
        "edges": [
            {"source_node_id": "start", "target_node_id": "llm"},
            {"source_node_id": "llm", "target_node_id": "tool"},
            {"source_node_id": "tool", "target_node_id": "end"},
        ],
    }


@pytest.mark.asyncio
async def test_create_workflow_rejects_duplicate_name() -> None:
    unit_of_work = FakeWorkflowsUnitOfWork()
    actor = actor_with_workflow_permissions()
    handler = CreateWorkflowHandler(lambda: unit_of_work, FixedClock())
    command = CreateWorkflowCommand(
        actor=actor,
        name="Support Flow",
        description=None,
        draft_definition=default_workflow_definition(),
    )

    workflow = await handler.handle(command)

    assert workflow.name == "Support Flow"
    assert unit_of_work.committed
    with pytest.raises(WorkflowAlreadyExistsError):
        await handler.handle(command)


@pytest.mark.asyncio
async def test_workflow_handlers_update_validate_publish_and_catalog_read_version() -> None:
    unit_of_work = FakeWorkflowsUnitOfWork()
    actor = actor_with_workflow_permissions()
    model_catalog = FakeModelCatalog(active_chat_model(actor.team_id))
    tool_catalog = FakeToolCatalog(active_tool(actor.team_id))
    create_handler = CreateWorkflowHandler(lambda: unit_of_work, FixedClock())
    workflow = await create_handler.handle(
        CreateWorkflowCommand(
            actor=actor,
            name="Support Flow",
            description="Answers questions",
            draft_definition=default_workflow_definition(),
        )
    )
    await UpdateWorkflowDraftHandler(lambda: unit_of_work, FixedClock()).handle(
        UpdateWorkflowDraftCommand(
            actor=actor,
            workflow_id=workflow.id,
            draft_definition=workflow_definition_with_model_and_tool(),
        )
    )

    validation = await ValidateWorkflowDraftHandler(
        lambda: unit_of_work,
        model_catalog,
        tool_catalog,
    ).handle(ValidateWorkflowDraftQuery(actor=actor, workflow_id=workflow.id))
    workflow_version = await PublishWorkflowHandler(
        lambda: unit_of_work,
        model_catalog,
        tool_catalog,
        FixedClock(),
    ).handle(PublishWorkflowCommand(actor=actor, workflow_id=workflow.id))

    catalog = WorkflowCatalogService(
        GetWorkflowVersionHandler(lambda: unit_of_work),
        GetLatestPublishedWorkflowVersionHandler(lambda: unit_of_work),
    )
    latest = await catalog.get_latest_published_version(
        team_id=actor.team_id,
        workflow_id=workflow.id,
    )
    fetched = await catalog.get_workflow_version(
        team_id=actor.team_id,
        workflow_version_id=workflow_version.id,
    )
    read_workflow = await GetWorkflowForActorHandler(lambda: unit_of_work).handle(
        GetWorkflowForActorQuery(actor=actor, workflow_id=workflow.id)
    )
    listed_workflows = await ListWorkflowsForActorHandler(lambda: unit_of_work).handle(
        ListWorkflowsForActorQuery(actor=actor)
    )

    assert validation.is_valid
    assert workflow_version.version_number == 1
    assert latest == fetched == workflow_version
    assert read_workflow.latest_version_number == 1
    assert listed_workflows == (read_workflow,)
    assert model_catalog.requests == [model_catalog.model.id, model_catalog.model.id]
    assert tool_catalog.requests == [tool_catalog.tool.id, tool_catalog.tool.id]


@pytest.mark.asyncio
async def test_create_workflow_requires_permission() -> None:
    unit_of_work = FakeWorkflowsUnitOfWork()
    actor = ActorContext(
        user_id=UUID("00000000-0000-7000-8000-000000000001"),
        team_id=UUID("00000000-0000-7000-8000-000000000002"),
        membership_id=UUID("00000000-0000-7000-8000-000000000003"),
        role="viewer",
        permissions=(),
    )
    handler = CreateWorkflowHandler(lambda: unit_of_work, FixedClock())

    with pytest.raises(WorkflowPermissionDeniedError):
        await handler.handle(
            CreateWorkflowCommand(
                actor=actor,
                name="Support Flow",
                description=None,
                draft_definition=default_workflow_definition(),
            )
        )
