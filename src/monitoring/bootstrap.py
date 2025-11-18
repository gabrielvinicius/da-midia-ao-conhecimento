from dataclasses import dataclass

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.monitoring.api.dependencies import (
    MonitoringDependencies,
    get_monitoring_dependencies,
)
from src.monitoring.application.analytics_queries import AnalyticsQueries
from src.monitoring.application.metrics_service import MetricsService
from src.monitoring.config.settings import AnalyticsSettings
from src.monitoring.domain.interfaces import IAnalyticsQueries
from src.monitoring.infrastructure.analytics_repository import AnalyticsRepository
from src.monitoring.infrastructure.prometheus_provider import PrometheusMetricsProvider


@dataclass
class MonitoringModule:
    analytics_queries: IAnalyticsQueries
    metrics_service: MetricsService


def build_monitoring_module(session: AsyncSession) -> MonitoringModule:
    settings = AnalyticsSettings()
    analytics_repository = AnalyticsRepository(db=session)
    metrics_provider = PrometheusMetricsProvider()
    analytics_queries = AnalyticsQueries(
        analytics_repo=analytics_repository,
        settings=settings,
    )
    metrics_service = MetricsService(
        metrics_provider=metrics_provider,
        analytics_repository=analytics_repository,
    )

    return MonitoringModule(
        analytics_queries=analytics_queries,
        metrics_service=metrics_service,
    )


def bind_monitoring_module(app: FastAPI, module: MonitoringModule) -> None:
    """Register FastAPI dependency overrides for monitoring components."""

    app.dependency_overrides[get_monitoring_dependencies] = (
        lambda: MonitoringDependencies(
            analytics_queries=module.analytics_queries,
            metrics_service=module.metrics_service,
        )
    )


__all__ = [
    "MonitoringModule",
    "build_monitoring_module",
    "bind_monitoring_module",
]
