"""Tarefas Celery do módulo de mídias (camada de montagem)."""
from __future__ import annotations

import structlog
from asgiref.sync import async_to_sync
from celery import shared_task

from src.shared.events.integration_events import TASK_MEDIA_RECOVER_UNSTARTED

logger = structlog.get_logger(__name__)


@shared_task(name=TASK_MEDIA_RECOVER_UNSTARTED, ignore_result=True)
def recover_unstarted_media_task() -> dict:
    """Periódica (Celery beat, fila leve): anuncia de novo as mídias cujo
    processamento nunca começou e marca como falha as que não começam."""
    from src.media_management.infrastructure.dependencies.recovery import (
        build_unstarted_media_recovery,
    )
    from src.shared.infrastructure.messaging.process_bus import process_event_bus
    from src.shared.infrastructure.database.db import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as session:
            return await build_unstarted_media_recovery(session, process_event_bus()).sweep()

    result = async_to_sync(_run)()
    if result.requeued or result.failed:
        logger.warning("unstarted_media.sweep_done", requeued=result.requeued, failed=result.failed)
    return {"requeued": result.requeued, "failed": result.failed}
