"""Central Celery application setup for the project.

This app replaces ad-hoc or missing Celery configuration and provides a
single entry point for workers and autodiscovery across modules.
"""
from __future__ import annotations

import os

from celery import Celery

# Import models to ensure they are registered with SQLAlchemy Base
# This prevents NoReferencedTableError for ForeignKeys when running workers
try:
    import src.user_management.infrastructure.user_model
    import src.notifications.infrastructure.models
    import src.media_management.infrastructure.orm.media_entity
    import src.media_processing.transcription.infrastructure.transcription_model
except ImportError:
    # Fallback if models aren't fully set up yet during scaffolding
    pass


def _default_broker() -> str:
    return os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")


def _default_backend() -> str | None:
    return os.getenv("CELERY_RESULT_BACKEND", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"))


def create_celery() -> Celery:
    app = Celery(
        "video_summarizer",
        broker=_default_broker(),
        backend=_default_backend(),
        include=[],
    )

    # Basic, safe defaults. Modules can override via env/configmap.
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("CELERY_TIMEZONE", "UTC"),
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")),
    )

    # Autodiscover tasks in namespaced packages
    app.autodiscover_tasks(
        [
            # New consolidated modules
            "src.media_processing",
            "src.text_analysis",

            # Existing task packages
            "src.notifications.tasks",
            "src.media_processing.transcription.tasks",
            "src.text_analysis.text_processing.tasks",
            "src.text_analysis.topic_modeling.tasks",
            "src.text_analysis.sentiment_analysis.tasks",
            "src.media_processing.video_processing.tasks",
        ]
    )

    return app


# Celery CLI entry point: "celery -A src.celery_app:celery worker"
celery = create_celery()

__all__ = ["celery", "create_celery"]