"""Encerra, no worker, a tarefa que ainda processa uma mídia parada."""
from __future__ import annotations

import asyncio

import structlog

from src.shared.events.integration_events import (
    TASK_MEDIA_TEXT_EXTRACTION,
    TASK_MEDIA_TRANSCRIPTION,
)

logger = structlog.get_logger(__name__)

_TASKS = {TASK_MEDIA_TRANSCRIPTION, TASK_MEDIA_TEXT_EXTRACTION}


class CeleryTaskTerminator:
    def __init__(self, celery_app=None, timeout_seconds: float = 3.0) -> None:
        self._app = celery_app
        self._timeout = timeout_seconds

    def _celery(self):
        if self._app is None:
            from src.celery_app import celery

            self._app = celery
        return self._app

    async def terminate(self, transcription_id: str, media_id: str) -> bool:
        return await asyncio.to_thread(self._terminate, transcription_id, media_id)

    def _terminate(self, transcription_id: str, media_id: str) -> bool:
        app = self._celery()
        active = app.control.inspect(timeout=self._timeout).active() or {}
        for worker, tasks in active.items():
            for task in tasks or []:
                kwargs = task.get("kwargs") or {}
                if task.get("name") not in _TASKS:
                    continue
                if kwargs.get("transcription_id") == transcription_id or kwargs.get("media_id") == media_id:
                    # SIGKILL: uma tarefa travada em código nativo (modelo na
                    # GPU) não responde a SIGTERM. O worker recria o processo.
                    app.control.revoke(task["id"], terminate=True, signal="SIGKILL")
                    logger.warning(
                        "stalled_monitor.task_terminated",
                        worker=worker,
                        task_id=task["id"],
                        media_id=media_id,
                    )
                    return True
        return False
