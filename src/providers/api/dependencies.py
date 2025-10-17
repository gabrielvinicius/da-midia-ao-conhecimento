"""
Providers API Dependencies - Dependency injection for provider services
Follows SOLID principles with clear separation of concerns.
"""
from typing import Annotated, Any
from fastapi import Depends, Request


def get_container(request: Request) -> dict:
    """Get the dependency injection container from request."""
    return request.app.state.container


def get_provider_registry(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get provider registry service."""
    return container.get("provider_registry")


def get_provider_selector(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get provider selector service."""
    return container.get("provider_selector")


def get_provider_health_checker(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get provider health checker service."""
    return container.get("provider_health_checker")


def get_provider_metrics(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get provider metrics service."""
    return container.get("provider_metrics")


def get_provider_configuration(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get provider configuration service."""
    return container.get("provider_configuration")


def get_provider_load_balancer(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get provider load balancer service."""
    return container.get("provider_load_balancer")


def get_provider_failover_manager(container: Annotated[dict, Depends(get_container)]) -> Any:
    """Get provider failover manager service."""
    return container.get("provider_failover_manager")