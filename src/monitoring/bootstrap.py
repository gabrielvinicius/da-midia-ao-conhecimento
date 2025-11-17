from dataclasses import dataclass

from dependency_injector import containers, providers
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession

from src.monitoring.api.dependencies import (
    MonitoringDependencies,
    get_monitoring_dependencies,
)
from src.monitoring.application.analytics_queries import AnalyticsQueries
from src.monitoring.application.metrics_service import MetricsService
from src.monitoring.config.settings import AnalyticsSettings
from src.monitoring.domain.interfaces import (
    IAnalyticsQueries,
    IAnalyticsRepository,
    IMetricsProvider,
)
from src.monitoring.infrastructure.analytics_repository import AnalyticsRepository
from src.monitoring.infrastructure.prometheus_provider import PrometheusMetricsProvider


class MonitoringContainer(containers.DeclarativeContainer):
    db: providers.Provider[AsyncSession] = providers.Dependency()

    # Configuration
    config = providers.Configuration()

    # Settings
    analytics_settings = providers.Singleton(AnalyticsSettings)

    # Infrastructure
    analytics_repository: providers.Provider[IAnalyticsRepository] = providers.Factory(
        AnalyticsRepository,
        db=db,
    )

    metrics_provider: providers.Provider[IMetricsProvider] = providers.Singleton(
        PrometheusMetricsProvider
    )

    # Application Services
    analytics_queries: providers.Provider[IAnalyticsQueries] = providers.Factory(
        AnalyticsQueries,
        analytics_repo=analytics_repository,
        settings=analytics_settings
    )

    metrics_service = providers.Singleton(
        MetricsService,
        metrics_provider=metrics_provider,
        analytics_repository=analytics_repository
    )


@dataclass
class MonitoringModule:
    analytics_queries: IAnalyticsQueries
    metrics_service: MetricsService


def build_monitoring_module(session: AsyncSession) -> MonitoringModule:
    container = MonitoringContainer(db=session)
    return MonitoringModule(
        analytics_queries=container.analytics_queries(),
        metrics_service=container.metrics_service(),
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
