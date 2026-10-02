"""Central Celery application setup for the project.

This app replaces ad-hoc or missing Celery configuration and provides a
single entry point for workers and autodiscovery across modules.
"""
from __future__ import annotations

import os

from celery import Celery
from celery.signals import (
    setup_logging,
    task_postrun,
    task_prerun,
    worker_process_init,
    worker_process_shutdown,
    worker_ready,
)

def _default_broker() -> str:
    return os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")


def _default_backend() -> str | None:
    return os.getenv("CELERY_RESULT_BACKEND", os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"))


# Folga além do prazo máximo de processamento antes de o Redis reentregar.
VISIBILITY_MARGIN_SECONDS = 3600


def visibility_timeout_seconds() -> int:
    from src.media_processing.config.settings import processing_settings

    return int(processing_settings.stall_maximum_hours * 3600) + VISIBILITY_MARGIN_SECONDS


def create_celery() -> Celery:
    app = Celery(
        "video_summarizer",
        broker=_default_broker(),
        backend=_default_backend(),
        include=[],
    )

    # Basic, safe defaults. Modules can override via env/configmap.
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone=os.getenv("CELERY_TIMEZONE", "UTC"),
        enable_utc=True,
        task_acks_late=True,
        worker_prefetch_multiplier=int(
            os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")
        ),
    )

    # Com acks_late, o Redis entrega de novo toda mensagem não confirmada
    # depois do visibility_timeout (1 hora por padrão), inclusive a que está
    # reservada enquanto outra roda. Uma análise longa seria reprocessada na
    # GPU. O limite passa a cobrir o prazo máximo de processamento.
    app.conf.broker_transport_options = {"visibility_timeout": visibility_timeout_seconds()}
    app.conf.result_backend_transport_options = {"visibility_timeout": visibility_timeout_seconds()}

    # Verificação periódica de mídias paradas. Roda no worker leve, iniciado
    # com --beat (docker-compose.yml): o pesado pode estar preso na tarefa.
    from src.media_processing.config.settings import processing_settings
    from src.media_management.config.settings import media_settings
    from src.shared.events.integration_events import (
        QUEUE_MAINTENANCE,
        TASK_MEDIA_RECOVER_UNSTARTED,
        TASK_MEDIA_SWEEP_STALLED,
    )

    app.conf.beat_schedule = {
        "sweep-stalled-processing": {
            "task": TASK_MEDIA_SWEEP_STALLED,
            "schedule": float(processing_settings.stall_check_interval_seconds),
            "options": {"queue": QUEUE_MAINTENANCE},
        },
        "recover-unstarted-media": {
            "task": TASK_MEDIA_RECOVER_UNSTARTED,
            "schedule": float(media_settings.unstarted_check_interval_seconds),
            "options": {"queue": QUEUE_MAINTENANCE},
        },
    }

    # Autodiscover tasks in namespaced packages
    app.autodiscover_tasks(
        [
            # Cada módulo declara as tarefas no próprio tasks.py (montagem).
            "src.media_management",
            "src.media_processing",
            "src.notifications",  # só assina eventos (avisos ao usuário)
            "src.text_analysis",
        ]
    )

    return app


@setup_logging.connect(weak=False)
def _configure_worker_logging(**_kwargs) -> None:
    """Workers usam o mesmo log estruturado da API (o Celery não o sobrescreve)."""
    from src.shared.infrastructure.observability.logging.logging_config import configure_logging

    configure_logging("video-summarizer-worker")


@task_prerun.connect(weak=False)
def _bind_task_context(task_id=None, task=None, kwargs=None, **_extra) -> None:
    """Cada linha de log da tarefa leva o correlation_id da requisição de origem."""
    import structlog

    structlog.contextvars.clear_contextvars()
    context = {"task_id": task_id, "task_name": getattr(task, "name", None)}
    for key in ("correlation_id", "media_id"):
        if (kwargs or {}).get(key):
            context[key] = str(kwargs[key])
    structlog.contextvars.bind_contextvars(**context)


@task_postrun.connect(weak=False)
def _clear_task_context(**_kwargs) -> None:
    import structlog

    structlog.contextvars.clear_contextvars()


@worker_process_init.connect(weak=False)
def _init_worker_tracing(**_kwargs) -> None:
    """Ativa o tracing em cada processo do worker (após o fork).

    Também recomeça o barramento de eventos do processo. Fica aqui, e não na
    montagem de um módulo, porque este sinal é registrado antes dos outros:
    se um módulo o recomeçasse, apagaria as inscrições feitas antes dele.
    """
    from src.shared.infrastructure.messaging.process_bus import reset_process_event_bus

    reset_process_event_bus()
    from src.shared.infrastructure.observability.tracing.tracer import configure_tracer

    configure_tracer("video-summarizer-worker")
    try:
        from opentelemetry.instrumentation.celery import CeleryInstrumentor

        CeleryInstrumentor().instrument()
    except Exception:  # instrumentação é opcional
        pass


@worker_ready.connect(weak=False)
def _start_gpu_stats(**_kwargs) -> None:
    """No worker com GPU, publica o uso da placa para o painel (gpu_stats)."""
    from src.shared.infrastructure.monitoring.gpu_stats import start_publisher

    start_publisher()


@worker_ready.connect(weak=False)
def _start_worker_metrics(**_kwargs) -> None:
    """O processo principal serve as métricas somadas dos processos filhos."""
    from src.shared.infrastructure.observability.metrics.exposition import start_metrics_server

    start_metrics_server()


@worker_process_shutdown.connect(weak=False)
def _forget_worker_process_metrics(pid=None, **_kwargs) -> None:
    from src.shared.infrastructure.observability.metrics.exposition import mark_process_dead

    mark_process_dead(pid or os.getpid())


# Celery CLI entry point: "celery -A src.celery_app:celery worker"
celery = create_celery()

__all__ = ["celery", "create_celery"]
