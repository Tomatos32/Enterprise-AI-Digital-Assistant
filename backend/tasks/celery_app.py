"""Celery Asynchronous Task Application Configuration Center."""

import os
from celery import Celery
from backend.core.config import settings

broker_url = os.getenv("CELERY_BROKER_URL", settings.REDIS_URL)
backend_url = os.getenv("CELERY_RESULT_BACKEND", settings.REDIS_URL)

celery_app = Celery(
    "enterprise_ai_tasks",
    broker=broker_url,
    backend=backend_url,
    include=["backend.tasks.ingestion_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    result_expires=86400,  # 24 hours result retention
)
