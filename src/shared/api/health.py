"""Health endpoints helpers."""

from __future__ import annotations

from fastapi import APIRouter

from src.shared.event_bus_factory import get_event_bus
from src.shared.infrastructure.prometheus_metrics import shared_metrics

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/bus", summary="Event bus health")
async def health_bus():
    try:
        bus = get_event_bus()
        status = "ok" if bus is not None else "unavailable"
        return {"status": status}
    except Exception as exc:  # pragma: no cover
        return {"status": "unavailable", "error": str(exc)}


@router.get("/metrics", summary="Prometheus metrics registry health")
async def health_metrics():
    try:
        # Touch the shared registry
        _ = shared_metrics.get_text_analysis_operations_total()
        return {"status": "ok"}
    except Exception as exc:  # pragma: no cover
        return {"status": "unavailable", "error": str(exc)}


__all__ = ["router"]
