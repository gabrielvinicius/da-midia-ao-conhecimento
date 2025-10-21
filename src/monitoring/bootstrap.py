from dependency_injector import containers, providers

from src.monitoring.domain.interfaces import IAnalyticsRepository, IMetricsProvider, IAnalyticsQueries
from src.monitoring.infrastructure.analytics_repository import AnalyticsRepository
from src.monitoring.infrastructure.prometheus_provider import PrometheusMetricsProvider
from src.monitoring.application.analytics_queries import AnalyticsQueries
from src.monitoring.application.metrics_service import MetricsService

from src.monitoring.config.settings import AnalyticsSettings

class MonitoringContainer(containers.DeclarativeContainer):
    wiring_config = containers.WiringConfiguration(modules=[".api.dependencies"])

    # Configuration
    config = providers.Configuration()

    # Settings
    analytics_settings = providers.Singleton(AnalyticsSettings)

    # Infrastructure
    analytics_repository: providers.Provider[IAnalyticsRepository] = providers.Factory(
        AnalyticsRepository,
        db=providers.Dependency()
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

    # Placeholder for other analytics/metrics services if needed
    # performance_analytics = providers.Factory(PerformanceAnalytics, ...)
    # quality_analytics = providers.Factory(QualityAnalytics, ...)
    # business_metrics = providers.Factory(BusinessMetrics, ...)
    # performance_metrics = providers.Factory(PerformanceMetrics, ...)
