from __future__ import annotations

from datetime import datetime, timezone
import os
from typing import Any, Dict

import structlog

from src.monitoring.domain.interfaces import (
    IAnalyticsRepository,
    IMetricsProvider,
    TimeRange,
)

logger = structlog.get_logger(__name__)

class MetricsService:
    def __init__(self, metrics_provider: IMetricsProvider, analytics_repository: IAnalyticsRepository):
        self.metrics_provider = metrics_provider
        self.analytics_repository = analytics_repository
        self._revenue_per_upload = float(os.getenv("BUSINESS_REVENUE_PER_UPLOAD", "12.0"))

    async def get_metrics_summary(self) -> Dict[str, Any]:
        raw_success_rates = await self.analytics_repository.get_success_failure_rates(TimeRange.LAST_WEEK)
        success_rates = {
            key: raw_success_rates.get(key, {})
            for key in ["media", "transcription", "summarization"]
        }
        user_metrics = await self.analytics_repository.get_user_activity_metrics()
        media_distribution = await self.analytics_repository.get_media_type_distribution()
        business_kpis = await self.get_business_kpis()
        performance_summary = await self.get_performance_summary()

        provider_metrics = {
            "available_metrics": self.metrics_provider.list_metrics(),
            "provider_type": getattr(self.metrics_provider, "provider_name", "Prometheus"),
        }

        return {
            "provider_metrics": provider_metrics,
            "success_rates": success_rates,
            "user_metrics": user_metrics,
            "media_distribution": media_distribution,
            "business_kpis": business_kpis,
            "performance_summary": performance_summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def health_check(self) -> Dict[str, Any]:
        metrics_available = len(self.metrics_provider.list_metrics())
        success_rates = await self.analytics_repository.get_success_failure_rates(TimeRange.LAST_DAY)
        media_stats = success_rates.get("media", {})
        status = "healthy"
        issues = []

        if (media_stats.get("failed") or 0) > (media_stats.get("total") or 1) * 0.3:
            status = "warning"
            issues.append("Taxa de falhas acima de 30% nas últimas 24h")

        if metrics_available == 0:
            status = "degraded"
            issues.append("Nenhuma métrica registrada no provedor")

        return {
            "status": status,
            "metrics_provider": "Operational" if metrics_available else "Unavailable",
            "performance_metrics": "Operational",  # derivado dos cálculos acima
            "total_metrics": metrics_available,
            "issues": issues,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }

    def track_media_upload_with_context(self, status: str, media_type: str, user_id: Any) -> None:
        self.metrics_provider.increment_counter("MEDIA_UPLOADS_TOTAL", labels={"status": status, "media_type": media_type, "user_id": str(user_id)})
        logger.info("media_upload_tracked", status=status, media_type=media_type, user_id=str(user_id))

    def track_user_activity(self, user_id: Any, action: str, resource_type: str) -> None:
        self.metrics_provider.increment_counter("USER_ACTIVITY_TOTAL", labels={"user_id": str(user_id), "action": action, "resource_type": resource_type})
        logger.info("user_activity_tracked", user_id=str(user_id), action=action, resource_type=resource_type)

    def track_processing_completion(self, operation: str, status: str, duration: float) -> None:
        if operation == "transcription":
            self.metrics_provider.increment_counter("TRANSCRIPTIONS_TOTAL", labels={"status": status})
            self.metrics_provider.observe_histogram("TRANSCRIPTION_DURATION", duration, labels={"status": status})
        elif operation == "summarization":
            self.metrics_provider.increment_counter("SUMMARIZATIONS_TOTAL", labels={"status": status})
            self.metrics_provider.observe_histogram("SUMMARIZATION_DURATION", duration, labels={"status": status})
        logger.info("processing_completion_tracked", operation=operation, status=status, duration=duration)

    def track_api_request(self, endpoint: str, method: str, duration: float, status_code: int) -> None:
        self.metrics_provider.increment_counter("REQUEST_COUNT", labels={"endpoint": endpoint, "method": method, "status_code": str(status_code)})
        self.metrics_provider.observe_histogram("REQUEST_LATENCY", duration, labels={"endpoint": endpoint, "method": method})
        logger.info("api_request_tracked", endpoint=endpoint, method=method, duration=duration, status_code=status_code)

    def track_system_resource(self, resource: str, usage: float, unit: str) -> None:
        self.metrics_provider.set_gauge(f"SYSTEM_RESOURCE_USAGE_{resource.upper()}", usage, labels={"unit": unit})
        logger.info("system_resource_tracked", resource=resource, usage=usage, unit=unit)

    def create_custom_metric(self, name: str, metric_type: str, description: str, labels: list) -> None:
        if metric_type == "counter":
            self.metrics_provider.create_dynamic_counter(name, description, labels)
        elif metric_type == "histogram":
            self.metrics_provider.create_dynamic_histogram(name, description, labels)
        elif metric_type == "gauge":
            self.metrics_provider.create_dynamic_gauge(name, description, labels)
        else:
            logger.warning("unsupported_metric_type", metric_type=metric_type)

    async def get_business_kpis(self) -> Dict[str, Any]:
        success_rates = await self.analytics_repository.get_success_failure_rates(TimeRange.LAST_MONTH)
        media_stats = success_rates.get("media", {})
        total_uploads = float(media_stats.get("total", 0))
        successful_uploads = float(media_stats.get("completed", 0))
        upload_success_rate = (successful_uploads / total_uploads * 100) if total_uploads else 0.0
        total_revenue = successful_uploads * self._revenue_per_upload

        return {
            "total_uploads": total_uploads,
            "successful_uploads": successful_uploads,
            "upload_success_rate_percent": round(upload_success_rate, 2),
            "total_revenue_usd": round(total_revenue, 2),
            "average_revenue_per_upload": self._revenue_per_upload,
            "processing_completions": float(media_stats.get("completed", 0)),
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def get_performance_summary(self) -> Dict[str, Any]:
        success_rates = await self.analytics_repository.get_success_failure_rates(TimeRange.LAST_WEEK)
        processing_trends = await self.analytics_repository.get_average_processing_times()
        media_stats = success_rates.get("media", {})

        total_processing = media_stats.get("total", 0)
        completed_processing = media_stats.get("completed", 0)
        failure_rate = ((media_stats.get("failed", 0) / total_processing) * 100) if total_processing else 0.0

        return {
            "request_metrics": {
                "total_requests": self.metrics_provider.get_metric_value("REQUEST_COUNT") or 0,
                "error_rate_percent": round(failure_rate, 2),
            },
            "processing_metrics": {
                "total_processing": total_processing,
                "completed": completed_processing,
                "avg_transcription_seconds": processing_trends.get("transcription_avg_seconds", 0.0),
                "avg_summarization_seconds": processing_trends.get("summarization_avg_seconds", 0.0),
            },
            "resource_metrics": {
                "cpu_usage_percent": self.metrics_provider.get_metric_value("SYSTEM_RESOURCE_USAGE_CPU") or 0,
                "memory_usage_percent": self.metrics_provider.get_metric_value("SYSTEM_RESOURCE_USAGE_MEMORY") or 0,
            },
            "throughput_metrics": {
                "media_por_dia": round(total_processing / 7, 2) if total_processing else 0,
                "conclusoes_por_hora": round(completed_processing / (7 * 24), 2) if completed_processing else 0,
                "taxa_conclusao_percent": round((completed_processing / total_processing * 100), 2) if total_processing else 0.0,
            },
            "overall_health": "Good" if failure_rate < 10 else "Warning",
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }
