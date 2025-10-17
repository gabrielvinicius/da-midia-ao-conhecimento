# src/metrics/bootstrap.py
from typing import Dict, Any

from src.metrics.infrastructure.prometheus_provider import PrometheusMetricsProvider

def bootstrap_metrics_module() -> Dict[str, Any]:
    """Constructs and returns the services for the metrics module."""
    metrics_provider = PrometheusMetricsProvider()

    return {
        "metrics_provider": metrics_provider,
    }
