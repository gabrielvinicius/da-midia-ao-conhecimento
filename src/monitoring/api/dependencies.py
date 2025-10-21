"""
Monitoring API Dependencies - Dependency injection for monitoring services
Follows SOLID principles with clear separation of concerns.
"""
from typing import Annotated, Any
from fastapi import Depends, Request

from src.monitoring.bootstrap import MonitoringContainer

def get_container(request: Request) -> MonitoringContainer:
    """Get the dependency injection container from request."""
    return request.app.state.container


def get_analytics_queries(container: Annotated[MonitoringContainer, Depends(get_container)]) -> Any:
    """Get analytics queries service."""
    return container.analytics_queries()


def get_metrics_service(container: Annotated[MonitoringContainer, Depends(get_container)]) -> Any:
    """Get main metrics service."""
    return container.metrics_service()