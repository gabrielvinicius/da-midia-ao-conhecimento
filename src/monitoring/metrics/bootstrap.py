# src/metrics/bootstrap.py
from typing import Dict, Any

from src.metrics.infrastructure.prometheus_provider import PrometheusMetricsProvider
from src.metrics.application.metrics_service import MetricsService
from src.metrics.application.services.business_metrics import BusinessMetrics
from src.metrics.application.services.performance_metrics import PerformanceMetrics

def bootstrap_metrics_module() -> Dict[str, Any]:
    """
    Constructs and returns the services for the metrics module following SOLID principles.
    
    All services depend on interfaces for maximum flexibility and testability.
    """
    # Core metrics provider (implements IMetricsProvider)
    metrics_provider = PrometheusMetricsProvider()
    
    # Specialized metrics services
    business_metrics = BusinessMetrics(metrics_provider=metrics_provider)
    performance_metrics = PerformanceMetrics(metrics_provider=metrics_provider)
    
    # Main metrics service that coordinates everything
    metrics_service = MetricsService(
        provider=metrics_provider,
        business_metrics=business_metrics,
        performance_metrics=performance_metrics
    )

    return {
        "metrics_provider": metrics_provider,
        "metrics_service": metrics_service,
        "business_metrics": business_metrics,
        "performance_metrics": performance_metrics,
    }
