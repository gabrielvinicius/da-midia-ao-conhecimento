from dataclasses import dataclass
from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import AsyncSession

from src.monitoring.domain.interfaces import IAnalyticsRepository, IMetricsProvider, IAnalyticsQueries
from src.monitoring.infrastructure.analytics_repository import AnalyticsRepository
from src.monitoring.infrastructure.prometheus_provider import PrometheusMetricsProvider
from src.monitoring.application.analytics_queries import AnalyticsQueries
from src.monitoring.application.metrics_service import MetricsService

from src.monitoring.config.settings import AnalyticsSettings


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
