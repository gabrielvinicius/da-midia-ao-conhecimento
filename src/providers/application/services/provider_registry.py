"""
Provider Registry Service - Single Responsibility: Provider registration and discovery
Follows SRP by handling only provider lifecycle management.
"""
from typing import Dict, List, Optional
import structlog
import asyncio

from src.providers.domain.interfaces import (
    IProviderRegistry, IProvider, ProviderType, ProviderCapability, 
    ProviderStatus, IProviderHealthChecker
)
from src.providers.domain.provider import BaseProvider, ProviderHealth

logger = structlog.get_logger(__name__)


class ProviderRegistry(IProviderRegistry):
    """
    Service responsible ONLY for provider registration and discovery.
    
    Single Responsibility: Handle provider lifecycle and registry operations.
    Open/Closed: Extensible for new provider types.
    Dependency Inversion: Depends on provider abstractions.
    """
    
    def __init__(self, health_checker: Optional[IProviderHealthChecker] = None):
        self._providers: Dict[str, Dict[str, IProvider]] = {}  # {type: {name: provider}}
        self.health_checker = health_checker
        self._initialized = False
    
    def register_provider(self, provider: IProvider) -> None:
        """
        Register a provider in the registry.
        
        Args:
            provider: Provider instance to register
        """
        try:
            provider_type = provider.get_type().value
            provider_name = provider.get_name()
            
            # Initialize type dictionary if needed
            if provider_type not in self._providers:
                self._providers[provider_type] = {}
            
            # Check for existing provider
            if provider_name in self._providers[provider_type]:
                logger.warning(
                    "provider.registration_override",
                    provider_name=provider_name,
                    provider_type=provider_type
                )
            
            # Register provider
            self._providers[provider_type][provider_name] = provider
            
            logger.info(
                "provider.registered",
                provider_name=provider_name,
                provider_type=provider_type,
                capabilities=len(provider.get_capabilities())
            )
            
        except Exception as e:
            logger.error(
                "provider.registration_failed",
                provider_name=provider.get_name(),
                provider_type=provider.get_type().value,
                error=str(e)
            )
            raise
    
    def unregister_provider(self, name: str, provider_type: ProviderType) -> bool:
        """
        Unregister a provider from the registry.
        
        Args:
            name: Provider name
            provider_type: Provider type
            
        Returns:
            bool: True if successfully unregistered
        """
        try:
            type_key = provider_type.value
            
            if type_key not in self._providers:
                logger.warning(
                    "provider.unregister_type_not_found",
                    provider_name=name,
                    provider_type=type_key
                )
                return False
            
            if name not in self._providers[type_key]:
                logger.warning(
                    "provider.unregister_not_found",
                    provider_name=name,
                    provider_type=type_key
                )
                return False
            
            # Cleanup provider before removing
            provider = self._providers[type_key][name]
            asyncio.create_task(provider.cleanup())
            
            # Remove from registry
            del self._providers[type_key][name]
            
            logger.info(
                "provider.unregistered",
                provider_name=name,
                provider_type=type_key
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "provider.unregister_failed",
                provider_name=name,
                provider_type=provider_type.value,
                error=str(e)
            )
            return False
    
    def get_provider(self, name: str, provider_type: ProviderType) -> Optional[IProvider]:
        """
        Get a specific provider.
        
        Args:
            name: Provider name
            provider_type: Provider type
            
        Returns:
            Provider instance or None if not found
        """
        type_key = provider_type.value
        
        if type_key not in self._providers:
            return None
        
        return self._providers[type_key].get(name)
    
    def list_providers(self, provider_type: Optional[ProviderType] = None) -> List[IProvider]:
        """
        List providers by type.
        
        Args:
            provider_type: Optional provider type filter
            
        Returns:
            List of providers
        """
        if provider_type:
            type_key = provider_type.value
            if type_key in self._providers:
                return list(self._providers[type_key].values())
            return []
        
        # Return all providers
        all_providers = []
        for provider_dict in self._providers.values():
            all_providers.extend(provider_dict.values())
        
        return all_providers
    
    def get_providers_by_capability(self, capability: ProviderCapability) -> List[IProvider]:
        """
        Get providers that support specific capability.
        
        Args:
            capability: Required capability
            
        Returns:
            List of providers with the capability
        """
        matching_providers = []
        
        for provider_dict in self._providers.values():
            for provider in provider_dict.values():
                if capability in provider.get_capabilities():
                    matching_providers.append(provider)
        
        logger.debug(
            "provider.capability_search",
            capability=capability.value,
            matching_count=len(matching_providers)
        )
        
        return matching_providers
    
    def get_active_providers(self, provider_type: Optional[ProviderType] = None) -> List[IProvider]:
        """
        Get active providers.
        
        Args:
            provider_type: Optional provider type filter
            
        Returns:
            List of active providers
        """
        all_providers = self.list_providers(provider_type)
        active_providers = []
        
        for provider in all_providers:
            # Check if provider has recent health check
            if hasattr(provider, 'health_status') and provider.health_status:
                if provider.health_status.is_healthy():
                    active_providers.append(provider)
            elif hasattr(provider, 'status'):
                if provider.status == ProviderStatus.ACTIVE:
                    active_providers.append(provider)
        
        logger.debug(
            "provider.active_providers_retrieved",
            total_providers=len(all_providers),
            active_providers=len(active_providers),
            provider_type=provider_type.value if provider_type else "all"
        )
        
        return active_providers
    
    async def initialize_all_providers(self, configurations: Dict[str, Dict[str, Dict[str, any]]]) -> Dict[str, Dict[str, bool]]:
        """
        Initialize all registered providers with their configurations.
        
        Args:
            configurations: Nested dict {provider_type: {provider_name: config}}
            
        Returns:
            Initialization results
        """
        results = {}
        
        for type_key, provider_dict in self._providers.items():
            results[type_key] = {}
            
            for provider_name, provider in provider_dict.items():
                try:
                    # Get configuration for this provider
                    config = configurations.get(type_key, {}).get(provider_name, {})
                    
                    # Initialize provider
                    success = await provider.initialize(config)
                    results[type_key][provider_name] = success
                    
                    if success:
                        logger.info(
                            "provider.initialized",
                            provider_name=provider_name,
                            provider_type=type_key
                        )
                    else:
                        logger.error(
                            "provider.initialization_failed",
                            provider_name=provider_name,
                            provider_type=type_key
                        )
                        
                except Exception as e:
                    results[type_key][provider_name] = False
                    logger.error(
                        "provider.initialization_error",
                        provider_name=provider_name,
                        provider_type=type_key,
                        error=str(e)
                    )
        
        self._initialized = True
        logger.info("provider.registry_initialization_completed", results=results)
        
        return results
    
    async def cleanup_all_providers(self) -> None:
        """Cleanup all registered providers."""
        cleanup_tasks = []
        
        for provider_dict in self._providers.values():
            for provider in provider_dict.values():
                cleanup_tasks.append(provider.cleanup())
        
        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)
        
        logger.info("provider.registry_cleanup_completed")
    
    def get_provider_summary(self) -> Dict[str, any]:
        """
        Get summary of all providers in registry.
        
        Returns:
            Summary dictionary
        """
        summary = {
            "total_providers": 0,
            "providers_by_type": {},
            "active_providers": 0,
            "capabilities_coverage": {},
            "initialized": self._initialized
        }
        
        # Count providers by type
        for type_key, provider_dict in self._providers.items():
            provider_count = len(provider_dict)
            summary["providers_by_type"][type_key] = provider_count
            summary["total_providers"] += provider_count
        
        # Count active providers
        active_providers = self.get_active_providers()
        summary["active_providers"] = len(active_providers)
        
        # Analyze capability coverage
        all_capabilities = set()
        for provider in self.list_providers():
            all_capabilities.update(provider.get_capabilities())
        
        for capability in all_capabilities:
            providers_with_cap = self.get_providers_by_capability(capability)
            summary["capabilities_coverage"][capability.value] = len(providers_with_cap)
        
        return summary
    
    def find_providers_by_name_pattern(self, pattern: str, provider_type: Optional[ProviderType] = None) -> List[IProvider]:
        """
        Find providers by name pattern.
        
        Args:
            pattern: Name pattern to search for
            provider_type: Optional provider type filter
            
        Returns:
            List of matching providers
        """
        providers = self.list_providers(provider_type)
        matching_providers = []
        
        pattern_lower = pattern.lower()
        
        for provider in providers:
            if pattern_lower in provider.get_name().lower():
                matching_providers.append(provider)
        
        logger.debug(
            "provider.pattern_search",
            pattern=pattern,
            provider_type=provider_type.value if provider_type else "all",
            matches=len(matching_providers)
        )
        
        return matching_providers
    
    def get_provider_types(self) -> List[ProviderType]:
        """Get all provider types that have registered providers."""
        return [ProviderType(type_key) for type_key in self._providers.keys()]
    
    def get_providers_count_by_type(self) -> Dict[ProviderType, int]:
        """Get count of providers by type."""
        return {
            ProviderType(type_key): len(provider_dict)
            for type_key, provider_dict in self._providers.items()
        }
    
    async def health_check_all_providers(self) -> Dict[str, Dict[str, Dict[str, any]]]:
        """
        Perform health check on all providers.
        
        Returns:
            Health check results organized by type and name
        """
        if not self.health_checker:
            logger.warning("provider.no_health_checker_configured")
            return {}
        
        try:
            health_results = await self.health_checker.check_all_providers_health()
            
            logger.info(
                "provider.health_check_completed",
                total_providers=sum(len(providers) for providers in health_results.values())
            )
            
            return health_results
            
        except Exception as e:
            logger.error("provider.health_check_failed", error=str(e))
            return {}
    
    def is_initialized(self) -> bool:
        """Check if registry has been initialized."""
        return self._initialized