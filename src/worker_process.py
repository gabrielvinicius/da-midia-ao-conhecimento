"""Montagem de cada processo de worker: o barramento de eventos com as
reações de todos os módulos, e o tracing.

Carregado pelo Celery só nos workers (``include`` em celery_app). A API e os
adaptadores que enviam tarefas importam celery_app, mas não este módulo, que
conhece os workers de todos os módulos.

Cada processo do Celery tem um barramento em memória (process_bus). As
tarefas publicam nele, e cada módulo reage ao que lhe interessa. Antes, cada
módulo se inscrevia por conta própria num sinal do Celery, a ordem entre eles
dependia da ordem em que as tarefas eram descobertas, e uma falha ao se
inscrever era só registrada: o worker seguia sem reagir a nada.
"""
from __future__ import annotations

from typing import Callable, Tuple

import structlog
from celery.signals import worker_process_init

from src.media_management.worker import bind_media_subscribers
from src.media_processing.worker import bind_processing_subscribers
from src.notifications.worker import bind_notification_subscribers
from src.shared.application.event_bus import SupportsEventBus
from src.shared.infrastructure.messaging.process_bus import (
    configure_process_subscribers,
    process_event_bus,
)

# media e notifications têm chave estrangeira para users. Sem o modelo
# carregado, o SQLAlchemy não resolvia a chave ao gravar ("could not find
# table 'users'") e a mídia parava em "uploaded" depois da transcrição.
import src.user_management.infrastructure.persistence.models  # noqa: E402,F401  isort: skip

logger = structlog.get_logger(__name__)

# A ordem importa: a mídia muda de estado antes de o aviso chegar ao usuário,
# que ao abrir a página já a vê atualizada.
WORKER_SUBSCRIBERS: Tuple[Callable[[SupportsEventBus], None], ...] = (
    bind_media_subscribers,  # estado da mídia
    bind_processing_subscribers,  # transcrição e pedido de análise
    bind_notification_subscribers,  # avisos ao usuário, por último
)


def bind_worker_subscribers(event_bus: SupportsEventBus) -> None:
    for bind in WORKER_SUBSCRIBERS:
        bind(event_bus)


@worker_process_init.connect(weak=False)
def init_worker_process(**_kwargs) -> None:
    """Após o fork: barramento novo, já com as reações, e tracing.

    O Celery engole a exceção de um sinal; por isso o barramento inscreve as
    reações ao ser criado, e uma falha aparece também em cada tarefa.
    """
    configure_process_subscribers(bind_worker_subscribers)
    try:
        process_event_bus()
    except Exception as exc:
        logger.error("worker.subscribers_failed", error=str(exc))

    from src.shared.infrastructure.observability.tracing.tracer import configure_tracer

    configure_tracer("sintese-worker")
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
    except Exception:  # instrumentação é opcional
        pass


__all__ = ["WORKER_SUBSCRIBERS", "bind_worker_subscribers", "init_worker_process"]
