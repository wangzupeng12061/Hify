from __future__ import annotations

from dataclasses import dataclass

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from hify.modules.jobs.api.dependencies import AuthenticationNotConfiguredAuthenticator
from hify.modules.jobs.api.router import create_jobs_router
from hify.modules.jobs.application.commands.mark_job_failed import MarkJobFailedHandler
from hify.modules.jobs.application.commands.mark_job_succeeded import MarkJobSucceededHandler
from hify.modules.jobs.application.commands.schedule_job import JobSchedulerService, ScheduleJobHandler
from hify.modules.jobs.application.job_claim_store import JobClaimStoreService
from hify.modules.jobs.application.queries.claim_next_job import ClaimNextJobHandler
from hify.modules.jobs.application.queries.get_job import GetJobForActorHandler, JobReaderService
from hify.modules.jobs.contracts.services import JobClaimStore, JobReader, JobScheduler
from hify.modules.jobs.infrastructure.database.uow import SqlAlchemyJobsUnitOfWork
from hify.shared.domain.clock import Clock, SystemClock


@dataclass(frozen=True, slots=True)
class JobsModule:
    router: APIRouter
    job_scheduler: JobScheduler
    job_reader: JobReader
    job_claim_store: JobClaimStore


def create_jobs_module(
    session_factory: async_sessionmaker[AsyncSession],
    *,
    clock: Clock | None = None,
) -> JobsModule:
    module_clock = clock or SystemClock()

    def unit_of_work_factory() -> SqlAlchemyJobsUnitOfWork:
        return SqlAlchemyJobsUnitOfWork(session_factory)

    schedule_job_handler = ScheduleJobHandler(unit_of_work_factory, module_clock)
    get_job_handler = GetJobForActorHandler(unit_of_work_factory)
    claim_next_job_handler = ClaimNextJobHandler(unit_of_work_factory, module_clock)
    mark_succeeded_handler = MarkJobSucceededHandler(unit_of_work_factory, module_clock)
    mark_failed_handler = MarkJobFailedHandler(unit_of_work_factory, module_clock)
    job_scheduler = JobSchedulerService(schedule_job_handler)
    job_reader = JobReaderService(unit_of_work_factory)
    job_claim_store = JobClaimStoreService(
        claim_next_job_handler,
        mark_succeeded_handler,
        mark_failed_handler,
    )
    router = create_jobs_router(
        get_job_handler=get_job_handler,
        request_authenticator=AuthenticationNotConfiguredAuthenticator(),
    )
    return JobsModule(
        router=router,
        job_scheduler=job_scheduler,
        job_reader=job_reader,
        job_claim_store=job_claim_store,
    )
