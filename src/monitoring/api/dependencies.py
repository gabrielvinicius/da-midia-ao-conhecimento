"""
Monitoring API Dependencies - Dependency injection for monitoring services
Follows SOLID principles with clear separation of concerns.
"""
from typing import Annotated, Any
from fastapi import Depends, Request


def get_container(request: Request) -> dict:
    """Get the dependency injection container from request."""
    return request.app.state.container


def get_analytics_queries(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get analytics queries service."""
    return container["analytics_queries"]


def get_performance_analytics(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get performance analytics service."""
    return container["performance_analytics"]


def get_quality_analytics(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get quality analytics service."""
    return container["quality_analytics"]


def get_analytics_repository(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get analytics repository."""
    return container["analytics_repository"]


def get_analytics_settings(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get analytics settings."""
    return container["analytics_settings"]


def get_metrics_service(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get main metrics service."""
    return container["metrics_service"]


def get_metrics_provider(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get metrics provider."""
    return container["metrics_provider"]


def get_business_metrics(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get business metrics service."""
    return container["business_metrics"]


def get_performance_metrics(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get performance metrics service."""
    return container["performance_metrics"]
