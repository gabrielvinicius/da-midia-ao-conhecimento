"""Provider registry for media_management bounded context."""
from __future__ import annotations

from src.media_management.application.ports import (
    EventBusPort,
    MediaMetricsPort,
)
from src.media_management.infrastructure.metrics.prometheus_metrics import (
    PrometheusMediaMetrics,
)
from src.shared.application.event_bus import SupportsEventBus


def get_media_metrics() -> MediaMetricsPort:
    return PrometheusMediaMetrics()


def get_event_bus(event_bus: SupportsEventBus | None) -> EventBusPort | None:
    """Retorna o event bus já construído pelo bootstrap.

    Mantemos a assinatura para compatibilidade com bootstraps que passem o bus,
    mas evitamos resolver singletons aqui para não acoplar o módulo a estado
    global. Se `event_bus` for None, retornamos None para falhar rápido.
    """
    return event_bus


__all__ = ["get_media_metrics", "get_event_bus"]
