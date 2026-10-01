"""Recupera as mídias enviadas cujo processamento nunca começou.

O envio grava a mídia e publica MediaUploaded; o processamento cria o seu
registro ao tratar o evento. Se a API cair entre um passo e outro, ou o
tratamento falhar, a mídia fica "enviada" sem nada na fila, e o monitor de
prazos do processamento não a enxerga. Este módulo, dono das mídias, as
anuncia de novo e, se mesmo assim nada começar, marca a falha.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import List, Optional

import structlog

from src.media_management.application.ports import (
    EventBusPort,
    ProcessingRecordsPort,
    RecoverableMediaPort,
)
from src.media_management.application.upload_events import upload_event_for
from src.shared.domain.events import MediaFailed

logger = structlog.get_logger(__name__)

GIVE_UP_MESSAGE = (
    "O processamento não chegou a começar. Tente novamente; se voltar a "
    "acontecer, verifique se os workers estão em execução."
)


@dataclass
class RecoveryResult:
    requeued: List[str] = field(default_factory=list)
    failed: List[str] = field(default_factory=list)


class UnstartedMediaRecovery:
    def __init__(
        self,
        media: RecoverableMediaPort,
        processing: ProcessingRecordsPort,
        event_bus: EventBusPort,
        grace_seconds: float,
        give_up_seconds: float,
    ) -> None:
        if give_up_seconds <= grace_seconds:
            raise ValueError("give_up_seconds deve ser maior que grace_seconds")
        self._media = media
        self._processing = processing
        self._event_bus = event_bus
        self._grace = grace_seconds
        self._give_up = give_up_seconds

    async def sweep(self, now: Optional[datetime.datetime] = None) -> RecoveryResult:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        result = RecoveryResult()
        # A folga evita disputar com um envio que ainda está sendo tratado.
        waiting = await self._media.list_waiting(now - datetime.timedelta(seconds=self._grace))
        if not waiting:
            return result
        started = await self._processing.media_with_processing([m.id for m in waiting])
        for media in waiting:
            if media.id in started:
                continue  # o monitor de prazos do processamento cuida dela
            age = (now - _aware(media.created_at)).total_seconds()
            if age >= self._give_up:
                await self._give_up_on(media)
                result.failed.append(str(media.id))
                continue
            logger.warning("unstarted_media.requeue", media_id=str(media.id), age_seconds=round(age))
            await self._event_bus.publish(
                upload_event_for(media, correlation_id=f"recovered-{media.id}")
            )
            result.requeued.append(str(media.id))
        return result

    async def _give_up_on(self, media) -> None:
        logger.warning("unstarted_media.marking_failed", media_id=str(media.id))
        media.mark_as_failed(GIVE_UP_MESSAGE)
        await self._media.update(media)
        # Quem avisa o usuário reage ao evento (notificações).
        await self._event_bus.publish(
            MediaFailed(
                media_id=str(media.id),
                user_id=str(media.user_id),
                stage="queue",
                error_message=GIVE_UP_MESSAGE,
            )
        )


def _aware(moment: datetime.datetime) -> datetime.datetime:
    # O banco grava em UTC sem fuso.
    if moment.tzinfo is None:
        return moment.replace(tzinfo=datetime.timezone.utc)
    return moment
