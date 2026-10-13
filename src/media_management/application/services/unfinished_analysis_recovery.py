"""Reconcilia análises concluídas e marca como falha as que pararam sem avisar.

Se o worker da análise morre (falta de memória, queda), nenhum
AnalysisFailed é publicado e a mídia ficaria "em análise" para sempre. A
mídia consulta conclusões por uma porta e usa o tempo desde que o texto ficou
pronto para identificar as demais que passaram do prazo.
"""
from __future__ import annotations

import datetime
from typing import List, Optional

import structlog

from src.media_management.application.ports import AnalysisCompletionRecordsPort, AnalyzingMediaPort, EventBusPort
from src.shared.domain.events import MediaFailed
from src.shared.domain.time.clock import utcnow

logger = structlog.get_logger(__name__)

PAGE_SIZE = 50

GIVE_UP_MESSAGE = "A análise do conteúdo não terminou no prazo. Tente reprocessar a mídia."


class UnfinishedAnalysisRecovery:
    def __init__(
        self, media: AnalyzingMediaPort, event_bus: EventBusPort, give_up_seconds: float,
        completions: Optional[AnalysisCompletionRecordsPort] = None,
    ) -> None:
        if give_up_seconds <= 0:
            raise ValueError("give_up_seconds deve ser positivo")
        self._media = media
        self._event_bus = event_bus
        self._give_up = give_up_seconds
        self._completions = completions

    async def sweep(self, now: Optional[datetime.datetime] = None) -> List[str]:
        """Ids das mídias marcadas como falha. As marcadas saem do estado
        "em análise", então cada página nova traz as seguintes."""
        updated_before = (now or utcnow()) - datetime.timedelta(seconds=self._give_up)
        failed: List[str] = []
        while True:
            page = await self._media.list_analyzing_since_before(updated_before, PAGE_SIZE)
            completed = await self._completions.completed_media_ids({m.id for m in page}) if self._completions else set()
            for media in page:
                if media.id in completed:
                    media.mark_as_completed()
                    await self._media.update(media)
                    logger.info("unfinished_analysis.reconciled", media_id=str(media.id))
                    continue
                await self._give_up_on(media)
                failed.append(str(media.id))
            if len(page) < PAGE_SIZE:
                return failed

    async def _give_up_on(self, media) -> None:
        logger.warning("unfinished_analysis.marking_failed", media_id=str(media.id))
        media.mark_as_failed(GIVE_UP_MESSAGE)
        await self._media.update(media)
        await self._event_bus.publish(
            MediaFailed(
                media_id=str(media.id),
                user_id=str(media.user_id),
                stage="analysis",
                error_message=GIVE_UP_MESSAGE,
            )
        )
