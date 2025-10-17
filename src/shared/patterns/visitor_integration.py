"""
Integration of Visitor Pattern with existing Decorator and other patterns
"""
from typing import Any, Dict, List, Optional, Callable
from functools import wraps

from src.shared.decorators.base_decorator import BaseAsyncDecorator
from src.shared.patterns.visitor import (
    IVisitor, IVisitable, VisitorChain, VisitorRegistry, VisitorResult
)


class VisitorDecorator(BaseAsyncDecorator):
    """Decorator that applies Visitor Pattern to service methods"""
    
    def __init__(
        self,
        visitor_names: List[str] = None,
        visitor_chain: VisitorChain = None,
        data_builder: Callable = None,
        result_processor: Callable = None
    ):
        super().__init__("visitor")
        self.visitor_names = visitor_names or []
        self.visitor_chain = visitor_chain
        self.data_builder = data_builder or self._default_data_builder
        self.result_processor = result_processor or self._default_result_processor
        self.visit_results: Optional[Dict[str, Any]] = None
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Build visitable data structure before method execution"""
        
        # Build visitable elements from method arguments
        visitable_elements = self.data_builder(*args, **kwargs)
        
        # Store for use in after_execution
        self._visitable_elements = visitable_elements
        
        return None  # Continue with normal execution
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Apply visitors after method execution"""
        
        if not hasattr(self, '_visitable_elements'):
            return result
        
        try:
            # Create visitor chain if not provided
            if not self.visitor_chain and self.visitor_names:
                self.visitor_chain = VisitorRegistry.create_visitor_chain(self.visitor_names)
            
            if self.visitor_chain:
                # Apply visitor chain to elements
                if isinstance(self._visitable_elements, list):
                    # Visit multiple elements
                    combined_results = {}
                    for i, element in enumerate(self._visitable_elements):
                        element_results = self.visitor_chain.visit_element(element)
                        combined_results[f"element_{i}"] = element_results
                    self.visit_results = combined_results
                else:
                    # Visit single element
                    self.visit_results = self.visitor_chain.visit_element(self._visitable_elements)
                
                # Process visitor results and combine with original result
                final_result = self.result_processor(result, self.visit_results)
                return final_result
        
        except Exception as e:
            # If visitor processing fails, return original result
            return result
        
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Handle visitor exceptions"""
        pass
    
    def _default_data_builder(self, *args, **kwargs) -> IVisitable:
        """Default data builder - override for specific use cases"""
        # This is a placeholder - should be overridden
        from src.shared.patterns.visitor import LeafElement
        return LeafElement("default", {"args": args, "kwargs": kwargs})
    
    def _default_result_processor(self, original_result: Any, visitor_results: Dict[str, Any]) -> Any:
        """Default result processor - combine original result with visitor results"""
        if isinstance(original_result, dict):
            return {
                **original_result,
                "visitor_analysis": visitor_results
            }
        else:
            return {
                "original_result": original_result,
                "visitor_analysis": visitor_results
            }


# Convenience decorators for specific visitor types
def analytics_visitor(visitor_names: List[str] = None):
    """Decorator for analytics visitor operations"""
    
    default_visitors = ["statistics_visitor", "trend_analysis_visitor"] if not visitor_names else visitor_names
    
    def data_builder(*args, **kwargs):
        from src.analytics.infrastructure.visitors.analytics_visitors import (
            AnalyticsDataContainer, MetricData, UserActivity, SystemEvent
        )
        
        # Extract analytics data from arguments
        container = AnalyticsDataContainer("method_analytics")
        
        # Look for analytics data in kwargs
        if "metrics" in kwargs:
            for metric_data in kwargs["metrics"]:
                if isinstance(metric_data, dict):
                    metric = MetricData(**metric_data)
                    container.add_metric(metric)
        
        if "activities" in kwargs:
            for activity_data in kwargs["activities"]:
                if isinstance(activity_data, dict):
                    activity = UserActivity(**activity_data)
                    container.add_activity(activity)
        
        if "events" in kwargs:
            for event_data in kwargs["events"]:
                if isinstance(event_data, dict):
                    event = SystemEvent(**event_data)
                    container.add_event(event)
        
        return container
    
    def decorator(func):
        visitor_decorator = VisitorDecorator(
            visitor_names=default_visitors,
            data_builder=data_builder
        )
        return visitor_decorator.decorate(func)
    
    return decorator


def admin_visitor(visitor_names: List[str] = None):
    """Decorator for admin visitor operations"""
    
    default_visitors = ["security_audit_visitor", "compliance_check_visitor"] if not visitor_names else visitor_names
    
    def data_builder(*args, **kwargs):
        from src.admin.infrastructure.visitors.admin_visitors import (
            AdminDataContainer, UserData, MediaData, SystemResource
        )
        
        container = AdminDataContainer("admin_analysis")
        
        # Extract admin data from arguments
        if "users" in kwargs:
            for user_data in kwargs["users"]:
                if isinstance(user_data, dict):
                    user = UserData(**user_data)
                    container.add_user(user)
        
        if "media" in kwargs:
            for media_data in kwargs["media"]:
                if isinstance(media_data, dict):
                    media = MediaData(**media_data)
                    container.add_media(media)
        
        if "resources" in kwargs:
            for resource_data in kwargs["resources"]:
                if isinstance(resource_data, dict):
                    resource = SystemResource(**resource_data)
                    container.add_resource(resource)
        
        return container
    
    def decorator(func):
        visitor_decorator = VisitorDecorator(
            visitor_names=default_visitors,
            data_builder=data_builder
        )
        return visitor_decorator.decorate(func)
    
    return decorator


def media_visitor(visitor_names: List[str] = None):
    """Decorator for media visitor operations"""
    
    default_visitors = ["media_analysis_visitor", "media_optimization_visitor"] if not visitor_names else visitor_names
    
    def data_builder(*args, **kwargs):
        from src.media_management.infrastructure.visitors.media_visitors import (
            MediaLibraryContainer, MediaFile, ProcessingResult, MediaCollection
        )
        
        container = MediaLibraryContainer("media_analysis")
        
        # Extract media data from arguments
        if "media_files" in kwargs:
            for media_data in kwargs["media_files"]:
                if isinstance(media_data, dict):
                    media_file = MediaFile(**media_data)
                    container.add_media_file(media_file)
        
        if "processing_results" in kwargs:
            for result_data in kwargs["processing_results"]:
                if isinstance(result_data, dict):
                    result = ProcessingResult(**result_data)
                    container.add_processing_result(result)
        
        if "collections" in kwargs:
            for collection_data in kwargs["collections"]:
                if isinstance(collection_data, dict):
                    collection = MediaCollection(**collection_data)
                    container.add_collection(collection)
        
        return container
    
    def decorator(func):
        visitor_decorator = VisitorDecorator(
            visitor_names=default_visitors,
            data_builder=data_builder
        )
        return visitor_decorator.decorate(func)
    
    return decorator


class VisitorPipelineIntegration:
    """Integration between Visitor Pattern and Chain of Responsibility"""
    
    @staticmethod
    def create_visitor_pipeline_stage(visitor_names: List[str]):
        """Create a pipeline stage that applies visitors"""
        
        from src.shared.patterns.chain_of_responsibility import BaseChainHandler, HandlerResult
        
        class VisitorPipelineHandler(BaseChainHandler):
            def __init__(self):
                super().__init__("VisitorHandler")
                self.visitor_chain = VisitorRegistry.create_visitor_chain(visitor_names)
            
            async def process(self, context) -> HandlerResult:
                """Apply visitors to context data"""
                
                # Extract visitable data from context
                if hasattr(context.request, 'visitable_data'):
                    visitor_results = self.visitor_chain.visit_element(context.request.visitable_data)
                    context.add_metadata("visitor_results", visitor_results)
                
                return HandlerResult.CONTINUE
        
        return VisitorPipelineHandler()


class VisitorTemplateIntegration:
    """Integration between Visitor Pattern and Template Method"""
    
    @staticmethod
    def create_visitor_template_stage():
        """Create a template method stage that applies visitors"""
        
        from src.shared.patterns.template_method import BaseAsyncDecorator
        
        class VisitorTemplateStage(BaseAsyncDecorator):
            def __init__(self, visitor_names: List[str]):
                super().__init__("visitor_template")
                self.visitor_names = visitor_names
            
            async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
                """Apply visitors after template execution"""
                
                # Check if result contains visitable data
                if hasattr(result, 'visitable_elements'):
                    visitor_chain = VisitorRegistry.create_visitor_chain(self.visitor_names)
                    
                    for element in result.visitable_elements:
                        visitor_results = visitor_chain.visit_element(element)
                        if not hasattr(result, 'visitor_analysis'):
                            result.visitor_analysis = {}
                        result.visitor_analysis[element.name] = visitor_results
                
                return result
        
        return VisitorTemplateStage


# Factory for creating integrated patterns
class IntegratedPatternFactory:
    """Factory for creating services with integrated design patterns"""
    
    @staticmethod
    def create_analytics_service_with_visitors():
        """Create analytics service with visitor integration"""
        
        from src.shared.decorators.decorator_factory import processing_operation
        
        class IntegratedAnalyticsService:
            
            @analytics_visitor(["statistics_visitor", "trend_analysis_visitor", "anomaly_detection_visitor"])
            @processing_operation("analytics", "comprehensive_analysis")
            async def analyze_comprehensive_data(
                self,
                metrics: List[Dict[str, Any]],
                activities: List[Dict[str, Any]],
                events: List[Dict[str, Any]]
            ) -> Dict[str, Any]:
                """Comprehensive analytics with visitor pattern"""
                
                return {
                    "metrics_count": len(metrics),
                    "activities_count": len(activities),
                    "events_count": len(events),
                    "analysis_completed": True
                }
        
        return IntegratedAnalyticsService()
    
    @staticmethod
    def create_admin_service_with_visitors():
        """Create admin service with visitor integration"""
        
        from src.shared.decorators.decorator_factory import processing_operation
        
        class IntegratedAdminService:
            
            @admin_visitor(["security_audit_visitor", "compliance_check_visitor", "system_cleanup_visitor"])
            @processing_operation("admin", "comprehensive_audit")
            async def perform_comprehensive_audit(
                self,
                users: List[Dict[str, Any]],
                media: List[Dict[str, Any]] = None,
                resources: List[Dict[str, Any]] = None
            ) -> Dict[str, Any]:
                """Comprehensive admin audit with visitor pattern"""
                
                return {
                    "users_audited": len(users),
                    "media_audited": len(media or []),
                    "resources_audited": len(resources or []),
                    "audit_completed": True
                }
        
        return IntegratedAdminService()
    
    @staticmethod
    def create_media_service_with_visitors():
        """Create media service with visitor integration"""
        
        from src.shared.decorators.decorator_factory import processing_operation
        
        class IntegratedMediaService:
            
            @media_visitor(["media_analysis_visitor", "media_optimization_visitor"])
            @processing_operation("media", "comprehensive_media_analysis")
            async def analyze_media_library(
                self,
                media_files: List[Dict[str, Any]],
                processing_results: List[Dict[str, Any]] = None,
                collections: List[Dict[str, Any]] = None
            ) -> Dict[str, Any]:
                """Comprehensive media analysis with visitor pattern"""
                
                return {
                    "files_analyzed": len(media_files),
                    "results_analyzed": len(processing_results or []),
                    "collections_analyzed": len(collections or []),
                    "analysis_completed": True
                }
        
        return IntegratedMediaService()


# Utility function to initialize all visitor registrations
def initialize_all_visitors():
    """Initialize and register all visitors"""
    
    # Register analytics visitors
    from src.analytics.infrastructure.visitors.analytics_visitors import register_analytics_visitors
    register_analytics_visitors()
    
    # Register admin visitors
    from src.admin.infrastructure.visitors.admin_visitors import register_admin_visitors
    register_admin_visitors()
    
    # Register media visitors
    from src.media_management.infrastructure.visitors.media_visitors import register_media_visitors
    register_media_visitors()
    
    print("✅ All visitor patterns registered successfully")


# Visitor management utilities
class VisitorManager:
    """Manager for visitor operations and monitoring"""
    
    @staticmethod
    def get_available_visitors() -> Dict[str, List[str]]:
        """Get all available visitors by category"""
        return {
            "analytics": VisitorRegistry.get_visitors_by_category("analytics"),
            "admin": VisitorRegistry.get_visitors_by_category("admin"),
            "media": VisitorRegistry.get_visitors_by_category("media"),
            "general": VisitorRegistry.get_visitors_by_category("general")
        }
    
    @staticmethod
    def create_custom_visitor_chain(
        visitor_configs: List[Dict[str, Any]]
    ) -> VisitorChain:
        """Create custom visitor chain from configurations"""
        
        visitors = []
        for config in visitor_configs:
            visitor_name = config["name"]
            visitor_kwargs = config.get("kwargs", {})
            visitor = VisitorRegistry.create_visitor(visitor_name, **visitor_kwargs)
            visitors.append(visitor)
        
        return VisitorChain(visitors)
    
    @staticmethod
    def get_visitor_performance_report(visitor_chain: VisitorChain) -> Dict[str, Any]:
        """Get performance report for visitor chain"""
        
        summary = visitor_chain.get_summary()
        
        # Add detailed performance metrics
        performance_data = {}
        for result in visitor_chain.results:
            visitor_name = result.metadata.get("visitor_name", "unknown")
            performance_data[visitor_name] = {
                "visited_count": result.visited_count,
                "errors": len(result.errors),
                "success": result.success,
                "metadata_keys": list(result.metadata.keys())
            }
        
        return {
            "summary": summary,
            "visitor_performance": performance_data,
            "recommendations": [
                "Monitor visitor error rates",
                "Optimize slow-performing visitors",
                "Consider parallel visitor execution for large datasets"
            ]
        }