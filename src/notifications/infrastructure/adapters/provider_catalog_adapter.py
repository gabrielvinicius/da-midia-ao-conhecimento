from __future__ import annotations

from typing import Dict, List

from src.shared.application.ports import PipelineProviderCatalogPort
from src.shared.application.provider_catalog import ProviderOption


class NotificationProvidersCatalogAdapter(PipelineProviderCatalogPort):
    """Expose only realtime delivery provider (Redis pubsub → WS)."""

    def list_pipeline_providers(self) -> Dict[str, List[ProviderOption]]:
        # Apenas provider público suportado hoje
        return {
            "notification_delivery": [
                ProviderOption(
                    name="redis_pubsub",
                    label="Redis → WebSocket",
                    description="Entrega realtime via Redis Pub/Sub para WS",
                    capabilities={"realtime": True},
                )
            ]
        }


__all__ = ["NotificationProvidersCatalogAdapter"]
