"""
Metrics API Dependencies - Dependency injection for metrics services
Follows SOLID principles with clear separation of concerns.
"""
from typing import Annotated, Any
from fastapi import Depends, Request


def get_container(request: Request) -> dict:
    """Get the dependency injection container from request."""
    return request.app.state.container


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