"""
Unified metrics collector - eliminating metrics duplication
"""
import time
import structlog
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime

logger = structlog.get_logger(__name__)

@dataclass
class MetricEvent:
    """Unified metric event structure"""
    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    metric_type: str = "counter"  # counter, gauge, histogram

class UnifiedMetricsCollector:
    """Single metrics collector for all domains - eliminating duplication"""
    
    def __init__(self):
        self._metrics: Dict[str, MetricEvent] = {}
    
    def record_operation_start(self, entity_type: str, entity_id: str, operation: str) -> str:
        """Record operation start - returns operation key for tracking"""
        operation_key = f"{entity_type}.{operation}.{entity_id}.{int(time.time())}"
        
        self.record_counter(
            name=f"{entity_type}_operations_started_total",
            labels={"operation": operation, "entity_id": entity_id}
        )
        
        # Store start time for duration calculation
        self._metrics[f"{operation_key}_start"] = MetricEvent(
            name=f"{entity_type}_operation_start",
            value=time.time(),
            labels={"operation": operation, "entity_id": entity_id},
            metric_type="gauge"
        )
        
        return operation_key
    
    def record_operation_success(self, operation_key: str, entity_type: str, result_data: Optional[Dict[str, Any]] = None):
        """Record successful operation completion"""
        start_key = f"{operation_key}_start"
        
        if start_key in self._metrics:
            duration = time.time() - self._metrics[start_key].value
            del self._metrics[start_key]  # Clean up
        else:
            duration = 0.0
        
        operation = operation_key.split('.')[1]  # Extract operation from key
        
        self.record_counter(
            name=f"{entity_type}_operations_completed_total",
            labels={"operation": operation, "status": "success"}
        )
        
        self.record_histogram(
            name=f"{entity_type}_operation_duration_seconds",
            value=duration,
            labels={"operation": operation, "status": "success"}
        )
        
        # Record result-specific metrics if provided
        if result_data:
            for key, value in result_data.items():
                if isinstance(value, (int, float)):
                    self.record_gauge(
                        name=f"{entity_type}_{operation}_{key}",
                        value=float(value),
                        labels={"operation": operation}
                    )
    
    def record_operation_failure(self, operation_key: str, entity_type: str, error: str):
        """Record failed operation"""
        start_key = f"{operation_key}_start"
        
        if start_key in self._metrics:
            duration = time.time() - self._metrics[start_key].value
            del self._metrics[start_key]  # Clean up
        else:
            duration = 0.0
        
        operation = operation_key.split('.')[1]  # Extract operation from key
        
        self.record_counter(
            name=f"{entity_type}_operations_completed_total",
            labels={"operation": operation, "status": "failed"}
        )
        
        self.record_histogram(
            name=f"{entity_type}_operation_duration_seconds",
            value=duration,
            labels={"operation": operation, "status": "failed"}
        )
        
        self.record_counter(
            name=f"{entity_type}_errors_total",
            labels={"operation": operation, "error_type": error}
        )
    
    def record_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, str]] = None):
        """Record counter metric"""
        self._store_metric(name, value, labels or {}, "counter")
    
    def record_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record gauge metric"""
        self._store_metric(name, value, labels or {}, "gauge")
    
    def record_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None):
        """Record histogram metric"""
        self._store_metric(name, value, labels or {}, "histogram")
    
    def _store_metric(self, name: str, value: float, labels: Dict[str, str], metric_type: str):
        """Store metric event"""
        metric = MetricEvent(
            name=name,
            value=value,
            labels=labels,
            metric_type=metric_type
        )
        
        # For counters, accumulate values
        if metric_type == "counter" and name in self._metrics:
            self._metrics[name].value += value
        else:
            self._metrics[name] = metric
        
        logger.debug(
            "metric.recorded",
            name=name,
            value=value,
            labels=labels,
            type=metric_type
        )
    
    def get_metrics(self) -> Dict[str, MetricEvent]:
        """Get all recorded metrics"""
        return self._metrics.copy()
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        self._metrics.clear()

# Global instance
unified_metrics = UnifiedMetricsCollector()