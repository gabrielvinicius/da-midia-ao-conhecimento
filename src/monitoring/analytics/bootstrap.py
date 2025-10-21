# src/analytics/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from src.analytics.application.queries.analytics_queries import AnalyticsQueries
from src.analytics.application.services.performance_analytics import PerformanceAnalytics
from src.analytics.application.services.quality_analytics import QualityAnalytics
from src.analytics.config.settings import AnalyticsSettings
from src.analytics.infrastructure.analytics_repository import AnalyticsRepository

def bootstrap_analytics_module(db_session: AsyncSession) -> Dict[str, Any]:
    """
    Constructs and returns the analytics services following SOLID principles.
    
    All services depend on interfaces for maximum flexibility and testability.
    """
    # Repository (implements IAnalyticsRepository)
    analytics_repository = AnalyticsRepository(db=db_session)
    
    # Settings
    analytics_settings = AnalyticsSettings()
    
    # Core analytics queries (implements IAnalyticsQueries)
    analytics_queries = AnalyticsQueries(
        analytics_repo=analytics_repository,
        settings=analytics_settings
    )
    
    # Specialized analytics services
    performance_analytics = PerformanceAnalytics(analytics_repo=analytics_repository)
    quality_analytics = QualityAnalytics(analytics_repo=analytics_repository)

    return {
        "analytics_repository": analytics_repository,
        "analytics_queries": analytics_queries,
        "performance_analytics": performance_analytics,
        "quality_analytics": quality_analytics,
        "analytics_settings": analytics_settings,
    }
