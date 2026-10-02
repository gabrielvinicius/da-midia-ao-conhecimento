"""Montagem dos avisos nos workers: assina os eventos do processamento.

Fica na raiz do módulo (camada de montagem) porque abre a sessão do banco e
usa o serviço de entrega pelo Redis.
"""
from __future__ import annotations

from uuid import UUID

import structlog

from src.notifications.application.pipeline_notices import NOTIFIED_EVENTS, notice_for
from src.notifications.bootstrap import bootstrap_pipeline_notification_service
from src.shared.application.event_bus import SupportsEventBus
from src.shared.domain.events import DomainEvent
from src.shared.infrastructure.database.db import AsyncSessionLocal

logger = structlog.get_logger(__name__)


async def notify_owner(event: DomainEvent) -> None:
    """Grava e entrega o aviso do evento. Uma falha aqui é registrada e não
    sobe a quem publicou: o aviso não pode desfazer a transcrição ou a análise
    (nem fazê-las rodar de novo na GPU)."""
    notice = notice_for(event)
    if notice is None:
        return
    try:
        async with AsyncSessionLocal() as session:
            await bootstrap_pipeline_notification_service(session).notify(
                user_id=UUID(str(notice.user_id)),
                message=notice.message,
                correlation_id=event.correlation_id,
                variables=notice.variables,
            )
    except Exception as exc:
        logger.warning("notifications.notice_failed", event_type=type(event).__name__, error=str(exc))


def bind_notification_subscribers(event_bus: SupportsEventBus) -> None:
    for event_type in NOTIFIED_EVENTS:
        event_bus.subscribe(event_type, notify_owner)


__all__ = ["bind_notification_subscribers", "notify_owner"]
