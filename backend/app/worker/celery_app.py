from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "neurosleep_twin",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks.ingestion", "app.worker.tasks.uploads"],
)
