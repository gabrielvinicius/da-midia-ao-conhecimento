"""Provider registry for media_management bounded context."""
from __future__ import annotations

from src.media_management.application.ports import (
    EventBusPort,
    MediaMetricsPort,
    StorageUploadPort,
)
from src.media_management.infrastructure.metrics.prometheus_metrics import (
    PrometheusMediaMetrics,
)
from src.shared.infrastructure.messaging.event_bus import SupportsEventBus
from src.storage.infrastructure.dependencies import StorageServiceFactory


def get_storage_uploader(factory: StorageServiceFactory) -> StorageUploadPort:
    class _Uploader(StorageUploadPort):
        async def upload(
            self,
            *,
            file_data: bytes,
            destination: str,
            content_type: str,
        ) -> dict:
            storage = factory.create_storage_service("local")
            return await storage.upload(
                file_data=file_data,
                destination=destination,
                content_type=content_type,
            )
    return _Uploader()


def get_media_metrics() -> MediaMetricsPort:
    return PrometheusMediaMetrics()


def get_event_bus(event_bus: SupportsEventBus | None) -> EventBusPort | None:
    """Retorna o event bus já construído pelo bootstrap.

    Mantemos a assinatura para compatibilidade com bootstraps que passem o bus,
    mas evitamos resolver singletons aqui para não acoplar o módulo a estado
    global. Se `event_bus` for None, retornamos None para falhar rápido.
    """
    return event_bus


__all__ = ["get_storage_uploader", "get_media_metrics", "get_event_bus"]
