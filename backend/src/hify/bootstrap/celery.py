from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]
from kombu import Queue  # type: ignore[import-untyped]

from hify.bootstrap.settings import Settings
from hify.modules.jobs.contracts.dto import JOB_QUEUE_NAMES


DEFAULT_CELERY_QUEUE = "events"
TASK_ROUTES: dict[str, dict[str, str]] = {
    "hify.modules.knowledge.infrastructure.tasks.ingest_document": {"queue": "ingestion"},
    "hify.modules.knowledge.infrastructure.tasks.embed_document": {"queue": "embedding"},
    "hify.modules.providers.infrastructure.tasks.batch_generate": {"queue": "llm_batch"},
    "hify.shared.infrastructure.tasks.dispatch_outbox": {"queue": "events"},
    "hify.modules.jobs.infrastructure.tasks.reconcile_jobs": {"queue": "maintenance"},
}


def create_celery_app(settings: Settings | None = None) -> Celery:
    resolved_settings = settings or Settings()
    broker_url = resolved_settings.celery_broker_url or resolved_settings.redis_url
    result_backend = resolved_settings.celery_result_backend_url
    app = Celery("hify", broker=broker_url, backend=result_backend)
    app.conf.update(
        task_default_queue=DEFAULT_CELERY_QUEUE,
        task_queues=tuple(Queue(name, routing_key=name) for name in JOB_QUEUE_NAMES),
        task_routes=TASK_ROUTES,
        worker_prefetch_multiplier=1,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        task_ignore_result=result_backend is None,
        task_soft_time_limit=resolved_settings.celery_task_soft_time_limit_seconds,
        task_time_limit=resolved_settings.celery_task_hard_time_limit_seconds,
        broker_transport_options={
            "visibility_timeout": resolved_settings.celery_visibility_timeout_seconds,
        },
    )
    return app


celery_app = create_celery_app()
