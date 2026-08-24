"""Core Celery Application Export and Compatibility Layer."""

from backend.tasks.celery_app import celery_app
from backend.tasks.ingestion_tasks import (
    async_ingest_document,
    async_parse_multimodal_file,
    parse_and_load_file,
)

__all__ = [
    "celery_app",
    "async_ingest_document",
    "async_parse_multimodal_file",
    "parse_and_load_file",
]
