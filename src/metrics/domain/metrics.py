# src/metrics/domain/metrics.py
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, Any, Optional, List
from uuid import UUID

# Import the new interfaces
from .interfaces import (
    MetricType, MetricCategory, AlertSeverity, IMetricsProvider
)

# Legacy compatibility - will be deprecated
class MetricsProvider(IMetricsProvider):
    """
    Legacy MetricsProvider - now extends the new IMetricsProvider interface.
    Maintained for backward compatibility.
    """
    
    @abstractmethod
    def increment_counter(self, name: str, labels: Optional[Dict[str, str]] = None, value: float = 1.0) -> None:
        pass

    @abstractmethod
    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        pass
    
    @abstractmethod
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        pass
    
    @abstractmethod
    def observe_summary(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        pass
    
    @abstractmethod
    def get_metric_value(self, name: str, labels: Optional[Dict[str, str]] = None) -> Optional[float]:
        pass
    
    @abstractmethod
    def list_metrics(self) -> List[str]:
        pass


# Domain entities
class MetricSample:
    """Represents a single metric sample."""
    
    def __init__(self, name: str, value: float, labels: Dict[str, str], timestamp: str):
        self.name = name
        self.value = value
        self.labels = labels
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp
        }


class AlertRule:
    """Represents an alerting rule."""
    
    def __init__(self, name: str, condition: str, threshold: float, severity: AlertSeverity):
        self.name = name
        self.condition = condition
        self.threshold = threshold
        self.severity = severity
        self.enabled = True
    
    def evaluate(self, current_value: float) -> bool:
        """Evaluate if the rule should trigger."""
        if self.condition == "greater_than":
            return current_value > self.threshold
        elif self.condition == "less_than":
            return current_value < self.threshold
        elif self.condition == "equals":
            return current_value == self.threshold
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "condition": self.condition,
            "threshold": self.threshold,
            "severity": self.severity.value,
            "enabled": self.enabled
        }


class CustomMetric:
    """Represents a custom application metric."""
    
    def __init__(self, name: str, metric_type: MetricType, description: str, labels: List[str]):
        self.name = name
        self.metric_type = metric_type
        self.description = description
        self.labels = labels
        self.created_at = "2024-01-01T00:00:00Z"  # Would use actual timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "description": self.description,
            "labels": self.labels,
            "created_at": self.created_at
        }