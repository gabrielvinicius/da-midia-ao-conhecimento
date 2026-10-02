"""Liga os avisos ao barramento de cada processo de worker (sem tarefas próprias)."""
from __future__ import annotations

import structlog
from celery.signals import worker_process_init

from src.notifications.worker import bind_notification_subscribers
from src.shared.infrastructure.messaging.process_bus import process_event_bus

logger = structlog.get_logger(__name__)


@worker_process_init.connect(weak=False)
def setup_notification_subscribers(**_kwargs) -> None:
    bind_notification_subscribers(process_event_bus())
    logger.info("notifications.worker.subscribers_configured")
