from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "neurosleep_twin",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks.ingestion", "app.worker.tasks.uploads"],
)

if settings.demo_mode:
    # No separate worker process or Redis broker on a single free web dyno —
    # .delay() runs the same task function synchronously in-process instead.
    # Fine at demo scale (one small MIT-BIH record at a time); the eager
    # path executes identical task code, just without the queue.
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True
