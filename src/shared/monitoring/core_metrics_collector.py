# src/shared/monitoring/core_metrics_collector.py
"""
Core metrics collection functionality - Single Responsibility Principle
Separated from the original 578-line MetricsCollector God Class
"""

import time
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("core_metrics")


class MetricType(str, Enum):
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"


@dataclass
class MetricDefinition:
    """Definição de uma métrica personalizada."""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None
    registry: Optional[CollectorRegistry] = None


class CoreMetricsCollector:
    """
    Core metrics collection with Single Responsibility: 
    Create, register and maintain Prometheus metrics
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        self.registry = registry or CollectorRegistry()
        self.metrics: Dict[str, Any] = {}
        self._initialize_core_metrics()
    
    def _initialize_core_metrics(self):
        """Initialize essential application metrics"""
        
        # HTTP metrics
        self.metrics['http_requests'] = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code'],
            registry=self.registry
        )
        
        self.metrics['http_request_duration'] = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint'],
            registry=self.registry
        )
        
        # System metrics
        self.metrics['cpu_usage'] = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.metrics['memory_usage'] = Gauge(
            'system_memory_usage_bytes',
            'Memory usage in bytes',
            registry=self.registry
        )
        
        logger.info("Core metrics initialized")
    
    def register_custom_metric(self, definition: MetricDefinition) -> Any:
        """Register a custom metric"""
        
        if definition.name in self.metrics:
            logger.warning(f"Metric {definition.name} already exists")
            return self.metrics[definition.name]
        
        metric_class = {
            MetricType.COUNTER: Counter,
            MetricType.HISTOGRAM: Histogram,
            MetricType.GAUGE: Gauge,
        }.get(definition.metric_type)
        
        if not metric_class:
            raise ValueError(f"Unsupported metric type: {definition.metric_type}")
        
        kwargs = {
            'name': definition.name,
            'documentation': definition.description,
            'labelnames': definition.labels,
            'registry': definition.registry or self.registry
        }
        
        if definition.metric_type == MetricType.HISTOGRAM and definition.buckets:
            kwargs['buckets'] = definition.buckets
        
        metric = metric_class(**kwargs)
        self.metrics[definition.name] = metric
        
        logger.info(f"Registered custom metric: {definition.name}")
        return metric
    
    def get_metric(self, name: str) -> Optional[Any]:
        """Get metric by name"""
        return self.metrics.get(name)
    
    def increment_counter(self, name: str, labels: Dict[str, str] = None):
        """Increment a counter metric"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'inc'):
            if labels:
                metric.labels(**labels).inc()
            else:
                metric.inc()
    
    def observe_histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Observe a value in histogram"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'observe'):
            if labels:
                metric.labels(**labels).observe(value)
            else:
                metric.observe(value)
    
    def set_gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set gauge value"""
        metric = self.get_metric(name)
        if metric and hasattr(metric, 'set'):
            if labels:
                metric.labels(**labels).set(value)
            else:
                metric.set(value)
    
    def get_registry(self) -> CollectorRegistry:
        """Get the metrics registry"""
        return self.registry
    
    def get_metrics_count(self) -> int:
        """Get total number of registered metrics"""
        return len(self.metrics)
    
    def list_metric_names(self) -> List[str]:
        """List all metric names"""
        return list(self.metrics.keys())


# Default instance
core_metrics = CoreMetricsCollector()