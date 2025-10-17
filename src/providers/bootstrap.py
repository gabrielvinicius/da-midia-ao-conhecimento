"""
Providers module bootstrap - Dependency injection setup
Follows SOLID principles with clear service composition.
"""
from typing import Dict, Any

from src.providers.application.services.provider_registry import ProviderRegistry
from src.providers.application.services.provider_selector import ProviderSelector


def bootstrap_providers_module() -> Dict[str, Any]:
    """
    Bootstrap the providers module following SOLID principles.
    
    All services depend on interfaces for maximum flexibility and testability.
    """
    # Core provider registry
    provider_registry = ProviderRegistry()
    
    # Provider selector with registry dependency
    provider_selector = ProviderSelector(
        provider_registry=provider_registry,
        metrics_service=None  # Would be injected from metrics module
    )
    
    # Placeholder services (would be implemented with real functionality)
    provider_health_checker = None  # Would be ProviderHealthChecker(provider_registry)
    provider_metrics = None         # Would be ProviderMetrics(metrics_provider)
    provider_configuration = None   # Would be ProviderConfiguration(config_store)
    provider_load_balancer = None   # Would be ProviderLoadBalancer(provider_registry)
    provider_failover_manager = None # Would be ProviderFailoverManager(provider_registry)

    return {
        "provider_registry": provider_registry,
        "provider_selector": provider_selector,
        "provider_health_checker": provider_health_checker,
        "provider_metrics": provider_metrics,
        "provider_configuration": provider_configuration,
        "provider_load_balancer": provider_load_balancer,
        "provider_failover_manager": provider_failover_manager,
    }