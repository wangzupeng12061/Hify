from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import TracebackType
from typing import Self
from uuid import UUID

import pytest

from hify.modules.identity.contracts.dto import ActorContext
from hify.modules.jobs.application.commands.mark_job_failed import (
    MarkJobFailedCommand,
    MarkJobFailedHandler,
)
from hify.modules.jobs.application.commands.mark_job_succeeded import (
    MarkJobSucceededCommand,
    MarkJobSucceededHandler,
)
from hify.modules.jobs.application.commands.schedule_job import (
    ScheduleJobCommand,
    ScheduleJobHandler,
)
from hify.modules.jobs.application.queries.claim_next_job import ClaimNextJobHandler, ClaimNextJobQuery
from hify.modules.jobs.application.queries.get_job import GetJobForActorHandler, GetJobForActorQuery
from hify.modules.jobs.domain.entities import Job
from hify.modules.jobs.domain.errors import JobNotFoundError, JobPermissionDeniedError
from hify.modules.jobs.domain.value_objects import JobStatus
from hify.shared.domain.clock import Clock


NOW = datetime(2026, 6, 22, tzinfo=UTC)
TEAM_ID = UUID("00000000-0000-7000-8000-000000000001")
USER_ID = UUID("00000000-0000-7000-8000-000000000002")
MEMBERSHIP_ID = UUID("00000000-0000-7000-8000-000000000003")


class FixedClock(Clock):
    def now(self) -> datetime:
        return NOW


class FakeJobRepository:
    def __init__(self) -> None:
        self.items: dict[UUID, Job] = {}

    async def add(self, job: Job) -> None:
        self.items[job.id] = job

    async def save(self, job: Job) -> None:
        self.items[job.id] = job

    async def get_by_id(self, job_id: UUID) -> Job | None:
        return self.items.get(job_id)

    async def get_by_team_and_idempotency_key(
        self,
        *,
        team_id: UUID,
        idempotency_key: str,
    ) -> Job | None:
        for job in self.items.values():
            if job.team_id == team_id and job.idempotency_key == idempotency_key:
                return job
        return None

    async def claim_next(
        self,
        *,
        queue: str,
        lease_owner: str,
        lease_expires_at: datetime,
        now: datetime,
    ) -> Job | None:
        for job in sorted(self.items.values(), key=lambda item: (item.available_at, item.id)):
            if job.queue.value == queue and job.status is JobStatus.PENDING:
                job.claim(lease_owner=lease_owner, lease_expires_at=lease_expires_at, now=now)
                return job
        return None


class FakeJobsUnitOfWork:
    def __init__(self) -> None:
        self.jobs = FakeJobRepository()
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


def actor_with_jobs_read() -> ActorContext:
    return ActorContext(
        user_id=USER_ID,
        team_id=TEAM_ID,
        membership_id=MEMBERSHIP_ID,
        role="admin",
        permissions=("jobs.read",),
    )


@pytest.mark.asyncio
async def test_schedule_job_is_idempotent_by_team_key() -> None:
    unit_of_work = FakeJobsUnitOfWork()
    handler = ScheduleJobHandler(lambda: unit_of_work, FixedClock())
    command = ScheduleJobCommand(
        team_id=TEAM_ID,
        queue="ingestion",
        job_kind="knowledge.document_ingestion",
        idempotency_key="document-1",
        payload={"document_id": "00000000-0000-7000-8000-000000000004"},
        created_by=USER_ID,
    )

    first = await handler.handle(command)
    second = await handler.handle(command)

    assert first.id == second.id
    assert len(unit_of_work.jobs.items) == 1
    assert unit_of_work.committed


@pytest.mark.asyncio
async def test_get_job_requires_read_permission() -> None:
    actor = ActorContext(
        user_id=USER_ID,
        team_id=TEAM_ID,
        membership_id=MEMBERSHIP_ID,
        role="viewer",
        permissions=(),
    )
    handler = GetJobForActorHandler(lambda: FakeJobsUnitOfWork())

    with pytest.raises(JobPermissionDeniedError):
        await handler.handle(
            GetJobForActorQuery(
                actor=actor,
                job_id=UUID("00000000-0000-7000-8000-000000000004"),
            )
        )


@pytest.mark.asyncio
async def test_claim_and_mark_job_result() -> None:
    unit_of_work = FakeJobsUnitOfWork()
    schedule_handler = ScheduleJobHandler(lambda: unit_of_work, FixedClock())
    claim_handler = ClaimNextJobHandler(lambda: unit_of_work, FixedClock())
    success_handler = MarkJobSucceededHandler(lambda: unit_of_work, FixedClock())
    job = await schedule_handler.handle(
        ScheduleJobCommand(
            team_id=TEAM_ID,
            queue="maintenance",
            job_kind="jobs.reconcile",
            idempotency_key="reconcile-1",
            payload={},
            created_by=USER_ID,
        )
    )

    claimed = await claim_handler.handle(
        ClaimNextJobQuery(queue="maintenance", lease_owner="worker-1", lease_seconds=300)
    )
    assert claimed is not None
    assert claimed.job.id == job.id
    assert claimed.job.attempt_count == 1

    completed = await success_handler.handle(MarkJobSucceededCommand(team_id=TEAM_ID, job_id=job.id))
    assert completed.status == "succeeded"


@pytest.mark.asyncio
async def test_mark_failed_schedules_retry_until_attempts_exhausted() -> None:
    unit_of_work = FakeJobsUnitOfWork()
    schedule_handler = ScheduleJobHandler(lambda: unit_of_work, FixedClock())
    claim_handler = ClaimNextJobHandler(lambda: unit_of_work, FixedClock())
    failed_handler = MarkJobFailedHandler(lambda: unit_of_work, FixedClock())
    job = await schedule_handler.handle(
        ScheduleJobCommand(
            team_id=TEAM_ID,
            queue="embedding",
            job_kind="knowledge.embedding",
            idempotency_key="embedding-1",
            payload={},
            created_by=USER_ID,
            max_attempts=2,
        )
    )
    await claim_handler.handle(
        ClaimNextJobQuery(queue="embedding", lease_owner="worker-1", lease_seconds=300)
    )

    retry_at = NOW + timedelta(minutes=1)
    retry = await failed_handler.handle(
        MarkJobFailedCommand(
            team_id=TEAM_ID,
            job_id=job.id,
            error_code="temporary_failure",
            error_message="try again",
            retry_at=retry_at,
        )
    )

    assert retry.status == "pending"
    assert retry.available_at == retry_at


@pytest.mark.asyncio
async def test_mark_succeeded_hides_cross_team_job_as_not_found() -> None:
    unit_of_work = FakeJobsUnitOfWork()
    handler = MarkJobSucceededHandler(lambda: unit_of_work, FixedClock())

    with pytest.raises(JobNotFoundError):
        await handler.handle(
            MarkJobSucceededCommand(
                team_id=TEAM_ID,
                job_id=UUID("00000000-0000-7000-8000-000000000099"),
            )
        )
