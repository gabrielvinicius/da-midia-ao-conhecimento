"""Tarefas Celery do módulo de mídias (camada de montagem)."""
from __future__ import annotations

import structlog
from asgiref.sync import async_to_sync
from celery import shared_task
from celery.signals import worker_process_init

from src.shared.events.integration_events import TASK_MEDIA_RECOVER_UNSTARTED

logger = structlog.get_logger(__name__)


@worker_process_init.connect(weak=False)
def setup_media_subscribers(**_kwargs) -> None:
    """Reações da mídia aos eventos, em cada processo de worker.

    Este módulo é descoberto antes do de avisos (celery_app), então o estado
    da mídia já está gravado quando o aviso chega ao usuário.
    """
    from src.media_management.worker import bind_media_subscribers
    from src.shared.infrastructure.messaging.process_bus import process_event_bus

    bind_media_subscribers(process_event_bus())
    logger.info("media_management.worker.subscribers_configured")


@shared_task(name=TASK_MEDIA_RECOVER_UNSTARTED, ignore_result=True)
def recover_unstarted_media_task() -> dict:
    """Periódica (Celery beat, fila leve): anuncia de novo as mídias cujo
    processamento nunca começou, marca como falha as que não começam e as
    que ficaram "em análise" além do prazo."""
    from src.media_management.infrastructure.dependencies.recovery import (
        build_unfinished_analysis_recovery,
        build_unstarted_media_recovery,
    )
    from src.shared.infrastructure.messaging.process_bus import process_event_bus
    from src.shared.infrastructure.database.db import AsyncSessionLocal

    async def _run():
        async with AsyncSessionLocal() as session:
            unstarted = await build_unstarted_media_recovery(session, process_event_bus()).sweep()
            analysis = await build_unfinished_analysis_recovery(session, process_event_bus()).sweep()
            return unstarted, analysis

    unstarted, analysis_failed = async_to_sync(_run)()
    if unstarted.requeued or unstarted.failed or analysis_failed:
        logger.warning(
            "media_recovery.sweep_done",
            requeued=unstarted.requeued,
            failed=unstarted.failed,
            analysis_failed=analysis_failed,
        )
    return {"requeued": unstarted.requeued, "failed": unstarted.failed, "analysis_failed": analysis_failed}
