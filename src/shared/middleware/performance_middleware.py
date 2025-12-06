"""Performance middleware registration and instrumentation helpers."""

from __future__ import annotations

import time
from typing import Any, Callable, Optional
from uuid import uuid4

from fastapi import FastAPI, Request
from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.shared.infrastructure.logging import get_logger

logger = get_logger("performance_middleware")


class PerformanceMetricsMiddleware(BaseHTTPMiddleware):
    """Record request metrics and expose tracing headers."""

    def __init__(
        self,
        app,
        *,
        metrics_resolver: Callable[[FastAPI], Optional[Any]],
        request_id_header: str = "X-Request-ID",
        process_time_header: str = "X-Process-Time",
    ) -> None:
        super().__init__(app)
        self._metrics_resolver = metrics_resolver
        self._request_id_header = request_id_header
        self._process_time_header = process_time_header
        self._metrics_service: Optional[Any] = None

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        start_time = time.perf_counter()
        request_id = request.headers.get(self._request_id_header, str(uuid4()))
        request.state.request_id = request_id  # type: ignore[attr-defined]

        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - exercised via FastAPI exception flow
            duration = time.perf_counter() - start_time
            self._record_metrics(request, duration, getattr(exc, "status_code", status.HTTP_500_INTERNAL_SERVER_ERROR))
            logger.error(
                "request_failed",
                request_id=request_id,
                method=request.method,
                path=str(request.url),
                duration=duration,
                error=str(exc),
            )
            raise

        duration = time.perf_counter() - start_time
        self._attach_headers(response, request_id, duration)
        self._record_metrics(request, duration, response.status_code)

        logger.info(
            "request_processed",
            request_id=request_id,
            method=request.method,
            path=str(request.url),
            status_code=response.status_code,
            duration=duration,
        )

        return response

    def _attach_headers(self, response: Response, request_id: str, duration: float) -> None:
        response.headers.setdefault(self._request_id_header, request_id)
        response.headers[self._process_time_header] = f"{duration:.6f}"

    def _record_metrics(self, request: Request, duration: float, status_code: int) -> None:
        metrics_service = self._resolve_metrics_service(request.app)
        if metrics_service is None:
            return

        try:
            metrics_service.track_api_request(request.url.path, request.method, duration, status_code)
        except Exception as exc:  # pragma: no cover - metrics backend issues
            logger.warning(
                "metrics_tracking_failed",
                error=str(exc),
                method=request.method,
                path=str(request.url),
            )

    def _resolve_metrics_service(self, app: FastAPI) -> Optional[Any]:
        if self._metrics_service is not None:
            return self._metrics_service

        metrics_service = None
        try:
            metrics_service = self._metrics_resolver(app)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("metrics_resolver_failed", error=str(exc))
        else:
            if metrics_service is not None:
                self._metrics_service = metrics_service

        return metrics_service


def _resolve_metrics_service(app: FastAPI) -> Optional[Any]:
    from src.monitoring.api.dependencies import (
        get_monitoring_dependencies,  # Local import to avoid cycles
    )

    provider = app.dependency_overrides.get(get_monitoring_dependencies)
    if provider is None or not callable(provider):
        return None

    dependencies = provider()
    metrics_service = getattr(dependencies, "metrics_service", None)
    if metrics_service is None:
        logger.warning("metrics_service_unavailable")
    return metrics_service


def register_performance_middleware(app: FastAPI) -> None:
    """Attach the performance middleware once per FastAPI application."""
    if getattr(app.state, "performance_middleware_registered", False):
        return

    app.add_middleware(
        PerformanceMetricsMiddleware,
        metrics_resolver=_resolve_metrics_service,
    )

    app.state.performance_middleware_registered = True
    logger.info("performance_middleware_registered")


__all__ = [
    "PerformanceMetricsMiddleware",
    "register_performance_middleware",
]
