"""Tarefas Celery do módulo de mídias (camada de montagem).

As reações da mídia aos eventos são registradas em src/worker_subscriptions.py.
"""
from __future__ import annotations

import asyncio

import structlog
from celery import shared_task

from src.shared.events.integration_events import TASK_MEDIA_RECOVER_UNSTARTED

logger = structlog.get_logger(__name__)


@shared_task(name=TASK_MEDIA_RECOVER_UNSTARTED)
def recover_unstarted_media_task() -> None:
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

    unstarted, analysis_failed = asyncio.run(_run())
    if unstarted.requeued or unstarted.failed or analysis_failed:
        logger.warning(
            "media_recovery.sweep_done",
            requeued=unstarted.requeued,
            failed=unstarted.failed,
            analysis_failed=analysis_failed,
        )
