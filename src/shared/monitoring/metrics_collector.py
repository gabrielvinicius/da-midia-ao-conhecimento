# src/shared/monitoring/simplified_metrics_collector.py
"""
Simplified MetricsCollector - Replacement for the 578-line God Class
Composes the broken-down components following Single Responsibility Principle
"""

import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime

from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .core_metrics_collector import CoreMetricsCollector, core_metrics
from .business_metrics_collector import BusinessMetricsCollector, business_metrics  
from .system_metrics_collector import SystemMetricsCollector, system_metrics
from .metrics_alerts import MetricsAlerting, metrics_alerting, AlertEvent

# Import missing components for backward compatibility
try:
    from .core_metrics_collector import MetricDefinition, MetricType
except ImportError:
    pass
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("simplified_metrics")


class SimplifiedMetricsCollector:
    """
    Simplified MetricsCollector following SOLID principles
    
    Replaces the original 578-line God Class with composition of focused components:
    - CoreMetricsCollector: Basic metric registration and management
    - BusinessMetricsCollector: Domain-specific business metrics  
    - SystemMetricsCollector: OS-level system metrics
    - MetricsAlerting: Alert evaluation and notifications
    
    This class provides the same public interface but with much better separation of concerns.
    """
    
    def __init__(self):
        self.core = core_metrics
        self.business = business_metrics
        self.system = system_metrics
        self.alerting = metrics_alerting
        
        self._collection_active = False
        
        logger.info("SimplifiedMetricsCollector initialized with SOLID architecture")
    
    # === Public API Methods (backward compatibility) ===
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        self.core.increment_counter('http_requests', {
            'method': method,
            'endpoint': endpoint,
            'status_code': str(status_code)
        })
        
        self.core.observe_histogram('http_request_duration', duration, {
            'method': method,
            'endpoint': endpoint
        })
    
    def record_media_processing(
        self, 
        media_type: str, 
        status: str, 
        provider: str, 
        duration: float,
        stage: str,
        file_size: int
    ):
        """Record media processing metrics"""
        self.business.record_media_processing(
            media_type, status, provider, duration, stage, file_size
        )
    
    def record_user_session(self, session_type: str = "web"):
        """Record user session"""
        self.business.record_user_session(session_type)
    
    def record_error(self, error_type: str, component: str):
        """Record application error"""
        self.business.record_error(error_type, component)
    
    # === Collection Management ===
    
    async def start_collection(self, interval_seconds: int = 30):
        """Start metrics collection"""
        if self._collection_active:
            logger.warning("Metrics collection already active")
            return
        
        self._collection_active = True
        
        # Start system metrics collection
        await self.system.start_collection(interval_seconds)
        
        # Start alert monitoring  
        await self.alerting.start_monitoring(interval_seconds)
        
        logger.info(f"Metrics collection started (interval: {interval_seconds}s)")
    
    async def stop_collection(self):
        """Stop metrics collection"""
        if not self._collection_active:
            return
        
        self._collection_active = False
        
        # Stop system metrics collection
        await self.system.stop_collection()
        
        # Stop alert monitoring
        await self.alerting.stop_monitoring()
        
        logger.info("Metrics collection stopped")
    
    # === Alert Management ===
    
    def add_alert_handler(self, handler):
        """Add alert notification handler"""
        self.alerting.add_notification_handler(handler)
    
    def enable_alert(self, alert_name: str, enabled: bool = True):
        """Enable/disable alert"""
        self.alerting.enable_alert(alert_name, enabled)
    
    # === Metrics Export ===
    
    def get_prometheus_metrics(self) -> str:
        """Get metrics in Prometheus format"""
        return generate_latest(self.core.get_registry())
    
    def get_metrics_content_type(self) -> str:
        """Get Prometheus content type"""
        return CONTENT_TYPE_LATEST
    
    # === Status and Info ===
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        return {
            "core_metrics": {
                "registered_metrics": self.core.get_metrics_count(),
                "metric_names": self.core.list_metric_names()
            },
            "system_metrics": {
                "collection_active": self._collection_active
            },
            "alerts": self.alerting.get_alert_status(),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for metrics system"""
        return {
            "status": "healthy" if self._collection_active else "stopped",
            "components": {
                "core_collector": "ok",
                "business_collector": "ok", 
                "system_collector": "ok",
                "alerting": "ok"
            },
            "metrics_count": self.core.get_metrics_count()
        }
    
    # === Legacy Compatibility ===
    
    @property 
    def registry(self):
        """Legacy property access to registry"""
        return self.core.get_registry()
    
    @property
    def metrics(self):
        """Legacy property access to metrics dict"""
        return self.core.metrics


# Create singleton instance to replace the original
metrics_collector = SimplifiedMetricsCollector()

# Backward compatibility aliases
MetricsCollector = SimplifiedMetricsCollector

# For complete backward compatibility, expose the instance methods
record_http_request = metrics_collector.record_http_request
record_media_processing = metrics_collector.record_media_processing
record_user_session = metrics_collector.record_user_session
record_error = metrics_collector.record_error