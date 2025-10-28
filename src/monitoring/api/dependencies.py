from typing import Annotated, Any
from fastapi import Depends, Request

from src.shared.application.modules import ModulesRegistry


def get_modules(request: Request) -> ModulesRegistry:
    """Get the bootstrapped modules registry from the request."""
    return request.app.state.modules


def get_analytics_queries(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    """Expose analytics queries."""
    return modules.monitoring.analytics_queries


def get_metrics_service(modules: Annotated[ModulesRegistry, Depends(get_modules)]) -> Any:
    """Expose the metrics service."""
    return modules.monitoring.metrics_service
