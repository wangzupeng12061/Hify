from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from hify.modules.workflows.domain.entities import Workflow, WorkflowVersion
from hify.modules.workflows.domain.value_objects import WorkflowStatus
from hify.modules.workflows.infrastructure.database.models import (
    WorkflowModel,
    WorkflowVersionModel,
)


class SqlAlchemyWorkflowRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workflow: Workflow) -> None:
        self._session.add(_workflow_to_model(workflow))

    async def save(self, workflow: Workflow) -> None:
        model = await self._session.get(WorkflowModel, workflow.id)
        if model is None:
            self._session.add(_workflow_to_model(workflow))
            return
        model.name = workflow.name
        model.description = workflow.description
        model.status = workflow.status.value
        model.draft_definition = dict(workflow.draft_definition)
        model.latest_version_number = workflow.latest_version_number
        model.version = workflow.version
        model.updated_at = workflow.updated_at

    async def get_by_id(self, workflow_id: UUID) -> Workflow | None:
        model = await self._session.get(WorkflowModel, workflow_id)
        if model is None:
            return None
        return _workflow_from_model(model)

    async def get_by_team_and_name(self, *, team_id: UUID, name: str) -> Workflow | None:
        statement = select(WorkflowModel).where(
            WorkflowModel.team_id == team_id,
            func.lower(WorkflowModel.name) == name.lower(),
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _workflow_from_model(model)

    async def list_by_team(self, *, team_id: UUID) -> tuple[Workflow, ...]:
        statement = (
            select(WorkflowModel)
            .where(WorkflowModel.team_id == team_id)
            .order_by(
                WorkflowModel.status.asc(),
                WorkflowModel.created_at.desc(),
                WorkflowModel.id.desc(),
            )
        )
        models = (await self._session.scalars(statement)).all()
        return tuple(_workflow_from_model(model) for model in models)


class SqlAlchemyWorkflowVersionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, workflow_version: WorkflowVersion) -> None:
        self._session.add(_workflow_version_to_model(workflow_version))

    async def get_by_id(self, workflow_version_id: UUID) -> WorkflowVersion | None:
        model = await self._session.get(WorkflowVersionModel, workflow_version_id)
        if model is None:
            return None
        return _workflow_version_from_model(model)

    async def get_latest_by_workflow_id(self, workflow_id: UUID) -> WorkflowVersion | None:
        statement = (
            select(WorkflowVersionModel)
            .where(WorkflowVersionModel.workflow_id == workflow_id)
            .order_by(WorkflowVersionModel.version_number.desc())
            .limit(1)
        )
        model = await self._session.scalar(statement)
        if model is None:
            return None
        return _workflow_version_from_model(model)


def _workflow_to_model(workflow: Workflow) -> WorkflowModel:
    return WorkflowModel(
        id=workflow.id,
        team_id=workflow.team_id,
        name=workflow.name,
        description=workflow.description,
        status=workflow.status.value,
        draft_definition=dict(workflow.draft_definition),
        latest_version_number=workflow.latest_version_number,
        version=workflow.version,
        created_by=workflow.created_by,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )


def _workflow_from_model(model: WorkflowModel) -> Workflow:
    return Workflow(
        id=model.id,
        team_id=model.team_id,
        name=model.name,
        description=model.description,
        status=WorkflowStatus(model.status),
        draft_definition=dict(model.draft_definition),
        latest_version_number=model.latest_version_number,
        version=model.version,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


def _workflow_version_to_model(workflow_version: WorkflowVersion) -> WorkflowVersionModel:
    return WorkflowVersionModel(
        id=workflow_version.id,
        team_id=workflow_version.team_id,
        workflow_id=workflow_version.workflow_id,
        version_number=workflow_version.version_number,
        name=workflow_version.name,
        description=workflow_version.description,
        definition=dict(workflow_version.definition),
        published_by=workflow_version.published_by,
        created_at=workflow_version.created_at,
    )


def _workflow_version_from_model(model: WorkflowVersionModel) -> WorkflowVersion:
    definition: dict[str, Any] = dict(model.definition)
    return WorkflowVersion(
        id=model.id,
        team_id=model.team_id,
        workflow_id=model.workflow_id,
        version_number=model.version_number,
        name=model.name,
        description=model.description,
        definition=definition,
        published_by=model.published_by,
        created_at=model.created_at,
    )
