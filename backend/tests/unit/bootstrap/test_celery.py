from __future__ import annotations

from hify.bootstrap.celery import DEFAULT_CELERY_QUEUE, create_celery_app
from hify.bootstrap.settings import Settings
from hify.modules.jobs.contracts.dto import JOB_QUEUE_NAMES


def test_celery_app_uses_named_queues_and_prefetch_one() -> None:
    app = create_celery_app(Settings(redis_url="redis://localhost:6379/9"))

    assert app.conf.task_default_queue == DEFAULT_CELERY_QUEUE
    assert app.conf.worker_prefetch_multiplier == 1
    assert app.conf.task_acks_late is True
    assert app.conf.task_reject_on_worker_lost is True
    assert {queue.name for queue in app.conf.task_queues} == set(JOB_QUEUE_NAMES)
