"""Backend Tasks Package."""

from backend.tasks.celery_app import celery_app
from backend.tasks.ingestion_tasks import async_ingest_document

__all__ = ["celery_app", "async_ingest_document"]
