"""
Provider Selector Service - Single Responsibility: Provider selection and load balancing
Follows SRP by handling only provider selection logic.
"""
from typing import List, Optional, Dict, Any
import random
import structlog

from src.providers.domain.interfaces import (
    IProviderSelector, IProviderRegistry, IProviderMetrics,
    IProvider, ProviderType, ProviderCapability
)
from src.providers.domain.provider import ProviderSelectionCriteria, ProviderMetrics

logger = structlog.get_logger(__name__)


class ProviderSelector(IProviderSelector):
    """
    Service responsible ONLY for provider selection and load balancing.
    
    Single Responsibility: Handle provider selection algorithms.
    Open/Closed: Extensible for new selection strategies.
    Dependency Inversion: Depends on registry and metrics abstractions.
    """
    
    def __init__(
        self,
        provider_registry: IProviderRegistry,
        metrics_service: Optional[IProviderMetrics] = None
    ):
        self.provider_registry = provider_registry
        self.metrics_service = metrics_service
        self._selection_strategies = {
            "round_robin": self._round_robin_selection,
            "least_loaded": self._least_loaded_selection,
            "random": self._random_selection,
            "performance_based": self._performance_based_selection,
            "cost_optimized": self._cost_optimized_selection
        }
        self._round_robin_counters: Dict[str, int] = {}
    
    async def select_best_provider(
        self,
        provider_type: ProviderType,
        required_capabilities: Optional[List[ProviderCapability]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> Optional[IProvider]:
        """
        Select the best provider based on criteria.
        
        Args:
            provider_type: Type of provider needed
            required_capabilities: Required capabilities
            preferences: Selection preferences
            
        Returns:
            Best matching provider or None
        """
        try:
            # Create selection criteria
            criteria = ProviderSelectionCriteria(
                provider_type=provider_type,
                required_capabilities=required_capabilities or [],
                **preferences if preferences else {}
            )
            
            # Get candidate providers
            candidates = await self._get_candidate_providers(criteria)
            
            if not candidates:
                logger.warning(
                    "provider.no_candidates_found",
                    provider_type=provider_type.value,
                    required_capabilities=[cap.value for cap in (required_capabilities or [])]
                )
                return None
            
            # Apply selection strategy
            strategy = criteria.load_balancing_strategy
            if strategy in self._selection_strategies:
                selected = await self._selection_strategies[strategy](candidates, criteria)
            else:
                logger.warning(
                    "provider.unknown_strategy",
                    strategy=strategy,
                    fallback="round_robin"
                )
                selected = await self._round_robin_selection(candidates, criteria)
            
            if selected:
                logger.info(
                    "provider.selected",
                    provider_name=selected.get_name(),
                    provider_type=provider_type.value,
                    strategy=strategy,
                    candidates_count=len(candidates)
                )
            
            return selected
            
        except Exception as e:
            logger.error(
                "provider.selection_failed",
                provider_type=provider_type.value,
                error=str(e)
            )
            return None
    
    async def select_providers_for_load_balancing(
        self,
        provider_type: ProviderType,
        required_capabilities: Optional[List[ProviderCapability]] = None,
        count: int = 2
    ) -> List[IProvider]:
        """
        Select multiple providers for load balancing.
        
        Args:
            provider_type: Type of provider needed
            required_capabilities: Required capabilities
            count: Number of providers to select
            
        Returns:
            List of selected providers
        """
        try:
            criteria = ProviderSelectionCriteria(
                provider_type=provider_type,
                required_capabilities=required_capabilities or []
            )
            
            candidates = await self._get_candidate_providers(criteria)
            
            if len(candidates) <= count:
                logger.info(
                    "provider.load_balancing_all_candidates",
                    provider_type=provider_type.value,
                    requested=count,
                    available=len(candidates)
                )
                return candidates
            
            # Select diverse providers for load balancing
            selected = await self._select_diverse_providers(candidates, count)
            
            logger.info(
                "provider.load_balancing_selected",
                provider_type=provider_type.value,
                selected_count=len(selected),
                selected_providers=[p.get_name() for p in selected]
            )
            
            return selected
            
        except Exception as e:
            logger.error(
                "provider.load_balancing_failed",
                provider_type=provider_type.value,
                error=str(e)
            )
            return []
    
    async def get_fallback_provider(
        self,
        primary_provider: IProvider,
        required_capabilities: Optional[List[ProviderCapability]] = None
    ) -> Optional[IProvider]:
        """
        Get fallback provider for primary provider.
        
        Args:
            primary_provider: Primary provider that failed
            required_capabilities: Required capabilities for fallback
            
        Returns:
            Fallback provider or None
        """
        try:
            criteria = ProviderSelectionCriteria(
                provider_type=primary_provider.get_type(),
                required_capabilities=required_capabilities or [],
                excluded_providers=[primary_provider.get_name()]
            )
            
            candidates = await self._get_candidate_providers(criteria)
            
            if not candidates:
                logger.warning(
                    "provider.no_fallback_found",
                    primary_provider=primary_provider.get_name(),
                    provider_type=primary_provider.get_type().value
                )
                return None
            
            # Select best fallback based on reliability
            fallback = await self._select_most_reliable_provider(candidates)
            
            if fallback:
                logger.info(
                    "provider.fallback_selected",
                    primary_provider=primary_provider.get_name(),
                    fallback_provider=fallback.get_name(),
                    provider_type=primary_provider.get_type().value
                )
            
            return fallback
            
        except Exception as e:
            logger.error(
                "provider.fallback_selection_failed",
                primary_provider=primary_provider.get_name(),
                error=str(e)
            )
            return None
    
    async def _get_candidate_providers(self, criteria: ProviderSelectionCriteria) -> List[IProvider]:
        """Get candidate providers that match criteria."""
        # Get all active providers of the required type
        all_providers = self.provider_registry.get_active_providers(criteria.provider_type)
        
        candidates = []
        
        for provider in all_providers:
            # Get metrics if available
            metrics = None
            if self.metrics_service:
                try:
                    metrics_data = await self.metrics_service.get_provider_performance_metrics(
                        provider.get_name(),
                        provider.get_type()
                    )
                    metrics = self._convert_to_provider_metrics(metrics_data)
                except Exception:
                    # Continue without metrics if not available
                    pass
            
            # Check if provider matches criteria
            if criteria.matches_provider(provider, metrics):
                candidates.append(provider)
        
        # Apply preferred providers ordering
        if criteria.preferred_providers:
            preferred = []
            others = []
            
            for provider in candidates:
                if provider.get_name() in criteria.preferred_providers:
                    preferred.append(provider)
                else:
                    others.append(provider)
            
            # Sort preferred providers by preference order
            preferred.sort(key=lambda p: criteria.preferred_providers.index(p.get_name()))
            candidates = preferred + others
        
        return candidates
    
    async def _round_robin_selection(
        self,
        candidates: List[IProvider],
        criteria: ProviderSelectionCriteria
    ) -> Optional[IProvider]:
        """Round robin selection strategy."""
        if not candidates:
            return None
        
        type_key = criteria.provider_type.value
        
        # Get current counter
        current_index = self._round_robin_counters.get(type_key, 0)
        
        # Select provider
        selected_provider = candidates[current_index % len(candidates)]
        
        # Update counter
        self._round_robin_counters[type_key] = (current_index + 1) % len(candidates)
        
        return selected_provider
    
    async def _least_loaded_selection(
        self,
        candidates: List[IProvider],
        criteria: ProviderSelectionCriteria
    ) -> Optional[IProvider]:
        """Select provider with least load."""
        if not candidates:
            return None
        
        if not self.metrics_service:
            # Fallback to random selection
            return await self._random_selection(candidates, criteria)
        
        least_loaded = None
        min_load = float('inf')
        
        for provider in candidates:
            try:
                metrics_data = await self.metrics_service.get_provider_performance_metrics(
                    provider.get_name(),
                    provider.get_type()
                )
                
                load = metrics_data.get('current_load', 0)
                
                if load < min_load:
                    min_load = load
                    least_loaded = provider
                    
            except Exception:
                # If metrics not available, consider as low load
                if min_load > 0:
                    min_load = 0
                    least_loaded = provider
        
        return least_loaded or candidates[0]
    
    async def _random_selection(
        self,
        candidates: List[IProvider],
        criteria: ProviderSelectionCriteria
    ) -> Optional[IProvider]:
        """Random selection strategy."""
        if not candidates:
            return None
        
        return random.choice(candidates)
    
    async def _performance_based_selection(
        self,
        candidates: List[IProvider],
        criteria: ProviderSelectionCriteria
    ) -> Optional[IProvider]:
        """Select provider based on performance metrics."""
        if not candidates:
            return None
        
        if not self.metrics_service:
            return await self._random_selection(candidates, criteria)
        
        best_provider = None
        best_score = -1
        
        for provider in candidates:
            try:
                metrics_data = await self.metrics_service.get_provider_performance_metrics(
                    provider.get_name(),
                    provider.get_type()
                )
                
                # Calculate performance score
                success_rate = metrics_data.get('success_rate_percentage', 100)
                avg_response_time = metrics_data.get('average_response_time_ms', 1000)
                
                # Higher score is better
                score = success_rate / (avg_response_time + 1)
                
                if score > best_score:
                    best_score = score
                    best_provider = provider
                    
            except Exception:
                # If metrics not available, use default score
                if best_score < 0:
                    best_provider = provider
                    best_score = 0
        
        return best_provider or candidates[0]
    
    async def _cost_optimized_selection(
        self,
        candidates: List[IProvider],
        criteria: ProviderSelectionCriteria
    ) -> Optional[IProvider]:
        """Select provider based on cost optimization."""
        if not candidates:
            return None
        
        if not self.metrics_service:
            return await self._random_selection(candidates, criteria)
        
        most_cost_effective = None
        best_cost_effectiveness = float('inf')
        
        for provider in candidates:
            try:
                metrics_data = await self.metrics_service.get_cost_metrics(
                    provider.get_name(),
                    provider.get_type()
                )
                
                cost_per_request = metrics_data.get('cost_per_request', 0)
                
                if cost_per_request < best_cost_effectiveness:
                    best_cost_effectiveness = cost_per_request
                    most_cost_effective = provider
                    
            except Exception:
                # If cost metrics not available, consider as free
                if best_cost_effectiveness > 0:
                    best_cost_effectiveness = 0
                    most_cost_effective = provider
        
        return most_cost_effective or candidates[0]
    
    async def _select_diverse_providers(self, candidates: List[IProvider], count: int) -> List[IProvider]:
        """Select diverse providers for load balancing."""
        if len(candidates) <= count:
            return candidates
        
        # Try to select providers from different vendors/types if possible
        selected = []
        remaining = candidates.copy()
        
        # First, try to get providers with different characteristics
        while len(selected) < count and remaining:
            # Select based on performance if metrics available
            if self.metrics_service:
                best = await self._performance_based_selection(remaining, None)
            else:
                best = remaining[0]
            
            selected.append(best)
            remaining.remove(best)
        
        return selected
    
    async def _select_most_reliable_provider(self, candidates: List[IProvider]) -> Optional[IProvider]:
        """Select most reliable provider based on metrics."""
        if not candidates:
            return None
        
        if not self.metrics_service:
            return candidates[0]
        
        most_reliable = None
        best_reliability = -1
        
        for provider in candidates:
            try:
                metrics_data = await self.metrics_service.get_provider_reliability_metrics(
                    provider.get_name(),
                    provider.get_type()
                )
                
                uptime = metrics_data.get('uptime_percentage', 100)
                error_rate = metrics_data.get('error_rate_percentage', 0)
                
                # Calculate reliability score
                reliability_score = uptime - error_rate
                
                if reliability_score > best_reliability:
                    best_reliability = reliability_score
                    most_reliable = provider
                    
            except Exception:
                # If metrics not available, consider as moderately reliable
                if best_reliability < 90:
                    best_reliability = 90
                    most_reliable = provider
        
        return most_reliable or candidates[0]
    
    def _convert_to_provider_metrics(self, metrics_data: Dict[str, Any]) -> ProviderMetrics:
        """Convert metrics data to ProviderMetrics object."""
        # This would convert from the metrics service format to our domain object
        # For now, return a basic implementation
        return ProviderMetrics(
            provider_name=metrics_data.get('provider_name', ''),
            provider_type=ProviderType(metrics_data.get('provider_type', 'storage')),
            total_requests=metrics_data.get('total_requests', 0),
            successful_requests=metrics_data.get('successful_requests', 0),
            failed_requests=metrics_data.get('failed_requests', 0),
            average_response_time_ms=metrics_data.get('average_response_time_ms', 0),
            uptime_percentage=metrics_data.get('uptime_percentage', 100),
            error_rate_percentage=metrics_data.get('error_rate_percentage', 0),
            current_load=metrics_data.get('current_load', 0),
            max_capacity=metrics_data.get('max_capacity', 100)
        )
    
    def get_selection_statistics(self) -> Dict[str, Any]:
        """Get selection statistics."""
        return {
            "round_robin_counters": self._round_robin_counters.copy(),
            "available_strategies": list(self._selection_strategies.keys()),
            "metrics_service_available": self.metrics_service is not None
        }