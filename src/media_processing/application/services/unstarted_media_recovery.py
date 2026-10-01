"""Recupera as mídias enviadas cujo processamento nunca começou.

O envio grava a mídia e publica MediaUploaded; o registro da transcrição é
criado por quem trata o evento. Se a API cair entre um passo e outro, ou o
tratamento falhar, a mídia fica "enviada" sem nada na fila, e o monitor de
prazos não a enxerga, porque ele parte das transcrições. Esta verificação,
executada junto com a dele, reenfileira essas mídias e, se mesmo assim o
processamento não começar, marca a mídia como falha para o usuário tentar
de novo.
"""
from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any, List, Optional

import structlog

from src.media_processing.application.ports import UnstartedMediaQueryPort
from src.shared.domain.events import MediaProcessingFailed

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
        query: UnstartedMediaQueryPort,
        upload_handler: Any,  # handle_media_uploaded(event): cria o registro e agenda
        event_bus: Any,
        grace_seconds: float,
        give_up_seconds: float,
    ) -> None:
        if give_up_seconds <= grace_seconds:
            raise ValueError("give_up_seconds deve ser maior que grace_seconds")
        self._query = query
        self._upload_handler = upload_handler
        self._event_bus = event_bus
        self._grace = grace_seconds
        self._give_up = give_up_seconds

    async def sweep(self, now: Optional[datetime.datetime] = None) -> RecoveryResult:
        now = now or datetime.datetime.now(datetime.timezone.utc)
        result = RecoveryResult()
        # Uma folga evita disputar com um envio que ainda está sendo tratado.
        candidates = await self._query.list_unstarted(
            now - datetime.timedelta(seconds=self._grace)
        )
        for item in candidates:
            media_id = str(item.upload.media_id)
            age = (now - _aware(item.uploaded_at)).total_seconds()
            if age >= self._give_up:
                await self._fail(item)
                result.failed.append(media_id)
                continue
            logger.warning(
                "unstarted_media.requeue", media_id=media_id, age_seconds=round(age)
            )
            await self._upload_handler.handle_media_uploaded(item.upload)
            result.requeued.append(media_id)
        return result

    async def _fail(self, item) -> None:
        upload = item.upload
        logger.warning("unstarted_media.marking_failed", media_id=str(upload.media_id))
        await self._event_bus.publish(
            MediaProcessingFailed(
                media_id=str(upload.media_id),
                stage="queue",
                error_message=GIVE_UP_MESSAGE,
                correlation_id=upload.correlation_id,
                metadata={"user_id": upload.user_id},
            )
        )


def _aware(moment: datetime.datetime) -> datetime.datetime:
    # O banco grava em UTC sem fuso.
    if moment.tzinfo is None:
        return moment.replace(tzinfo=datetime.timezone.utc)
    return moment
