from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends

from src.monitoring.application.analytics_queries import AnalyticsQueries
from src.monitoring.application.metrics_service import MetricsService


class MonitoringDependenciesNotConfigured(RuntimeError):
    pass


@dataclass(frozen=True)
class MonitoringDependencies:
    analytics_queries: AnalyticsQueries
    metrics_service: MetricsService


def get_monitoring_dependencies() -> MonitoringDependencies:
    raise MonitoringDependenciesNotConfigured(
        "Monitoring dependencies are not configured. Register providers in the lifespan handler."
    )


MonitoringDeps = Annotated[MonitoringDependencies, Depends(get_monitoring_dependencies)]


def get_analytics_queries(deps: MonitoringDeps) -> AnalyticsQueries:
    """Expose analytics queries."""
    return deps.analytics_queries


def get_metrics_service(deps: MonitoringDeps) -> MetricsService:
    """Expose the metrics service."""
    return deps.metrics_service


__all__ = [
    "MonitoringDependencies",
    "MonitoringDependenciesNotConfigured",
    "get_monitoring_dependencies",
    "get_analytics_queries",
    "get_metrics_service",
]
