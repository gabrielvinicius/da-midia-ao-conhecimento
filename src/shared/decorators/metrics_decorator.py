"""
Metrics Decorator for automatic performance monitoring
"""
import time
from typing import Any, Optional, Dict
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from .base_decorator import BaseAsyncDecorator


@dataclass
class MetricData:
    """Container for metric measurements"""
    operation_name: str
    module_name: str
    start_time: float
    end_time: Optional[float] = None
    duration_ms: Optional[float] = None
    success: bool = True
    error_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Thread-safe metrics collector - Singleton Pattern"""
    
    _instance = None
    _metrics: Dict[str, list[MetricData]] = defaultdict(list)
    _counters: Dict[str, int] = defaultdict(int)
    _timers: Dict[str, list[float]] = defaultdict(list)
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def record_operation(self, metric: MetricData) -> None:
        """Record operation metric"""
        key = f"{metric.module_name}.{metric.operation_name}"
        self._metrics[key].append(metric)
        
        # Update counters
        if metric.success:
            self._counters[f"{key}.success"] += 1
        else:
            self._counters[f"{key}.error"] += 1
        
        # Update timers
        if metric.duration_ms:
            self._timers[f"{key}.duration"].append(metric.duration_ms)
    
    def get_metrics_summary(self, module_name: str = None) -> Dict[str, Any]:
        """Get metrics summary for module or all"""
        summary = {
            "operations": {},
            "performance": {},
            "errors": {}
        }
        
        for key, metrics in self._metrics.items():
            if module_name and not key.startswith(module_name):
                continue
            
            total_ops = len(metrics)
            successful_ops = sum(1 for m in metrics if m.success)
            error_ops = total_ops - successful_ops
            
            durations = [m.duration_ms for m in metrics if m.duration_ms]
            avg_duration = sum(durations) / len(durations) if durations else 0
            max_duration = max(durations) if durations else 0
            min_duration = min(durations) if durations else 0
            
            summary["operations"][key] = {
                "total": total_ops,
                "successful": successful_ops,
                "errors": error_ops,
                "success_rate": (successful_ops / total_ops * 100) if total_ops > 0 else 0
            }
            
            summary["performance"][key] = {
                "avg_duration_ms": round(avg_duration, 2),
                "max_duration_ms": round(max_duration, 2),
                "min_duration_ms": round(min_duration, 2),
                "total_operations": total_ops
            }
            
            if error_ops > 0:
                error_types = defaultdict(int)
                for m in metrics:
                    if not m.success and m.error_type:
                        error_types[m.error_type] += 1
                
                summary["errors"][key] = dict(error_types)
        
        return summary
    
    def reset_metrics(self) -> None:
        """Reset all collected metrics"""
        self._metrics.clear()
        self._counters.clear()
        self._timers.clear()


class MetricsDecorator(BaseAsyncDecorator):
    """Decorator for automatic performance metrics collection"""
    
    def __init__(
        self, 
        operation_name: str,
        module_name: str,
        collect_args_metrics: bool = False,
        collect_result_metrics: bool = False
    ):
        super().__init__("metrics")
        self.operation_name = operation_name
        self.module_name = module_name
        self.collect_args_metrics = collect_args_metrics
        self.collect_result_metrics = collect_result_metrics
        self.collector = MetricsCollector()
        self.current_metric: Optional[MetricData] = None
    
    async def _before_execution(self, *args, **kwargs) -> Optional[Any]:
        """Start metrics collection"""
        self.current_metric = MetricData(
            operation_name=self.operation_name,
            module_name=self.module_name,
            start_time=time.time()
        )
        
        # Collect argument metrics if enabled
        if self.collect_args_metrics:
            self.current_metric.metadata.update({
                "args_count": len(args),
                "kwargs_count": len(kwargs),
                "input_size": self._calculate_input_size(args, kwargs)
            })
        
        return None
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Complete metrics collection on success"""
        if self.current_metric:
            self.current_metric.end_time = time.time()
            self.current_metric.duration_ms = (
                self.current_metric.end_time - self.current_metric.start_time
            ) * 1000
            self.current_metric.success = True
            
            # Collect result metrics if enabled
            if self.collect_result_metrics and result is not None:
                self.current_metric.metadata.update({
                    "result_type": type(result).__name__,
                    "output_size": self._calculate_output_size(result)
                })
            
            self.collector.record_operation(self.current_metric)
        
        return result
    
    async def _on_exception(self, exception: Exception, *args, **kwargs) -> None:
        """Complete metrics collection on error"""
        if self.current_metric:
            self.current_metric.end_time = time.time()
            self.current_metric.duration_ms = (
                self.current_metric.end_time - self.current_metric.start_time
            ) * 1000
            self.current_metric.success = False
            self.current_metric.error_type = type(exception).__name__
            self.current_metric.metadata["error_message"] = str(exception)
            
            self.collector.record_operation(self.current_metric)
    
    def _calculate_input_size(self, args: tuple, kwargs: dict) -> int:
        """Calculate approximate input data size"""
        size = 0
        
        for arg in args:
            if isinstance(arg, (str, bytes)):
                size += len(arg)
            elif isinstance(arg, (list, tuple, dict)):
                size += len(arg)
            elif hasattr(arg, '__len__'):
                try:
                    size += len(arg)
                except:
                    size += 1
            else:
                size += 1
        
        for value in kwargs.values():
            if isinstance(value, (str, bytes)):
                size += len(value)
            elif isinstance(value, (list, tuple, dict)):
                size += len(value)
            elif hasattr(value, '__len__'):
                try:
                    size += len(value)
                except:
                    size += 1
            else:
                size += 1
        
        return size
    
    def _calculate_output_size(self, result: Any) -> int:
        """Calculate approximate output data size"""
        if isinstance(result, (str, bytes)):
            return len(result)
        elif isinstance(result, (list, tuple, dict)):
            return len(result)
        elif hasattr(result, '__len__'):
            try:
                return len(result)
            except:
                return 1
        else:
            return 1


class PerformanceMetricsDecorator(MetricsDecorator):
    """Specialized decorator for performance-critical operations"""
    
    def __init__(self, operation_name: str, module_name: str, threshold_ms: float = 1000.0):
        super().__init__(operation_name, module_name, True, True)
        self.threshold_ms = threshold_ms
    
    async def _after_execution(self, result: Any, *args, **kwargs) -> Any:
        """Enhanced metrics with performance alerts"""
        result = await super()._after_execution(result, *args, **kwargs)
        
        # Check performance threshold
        if (self.current_metric and 
            self.current_metric.duration_ms and 
            self.current_metric.duration_ms > self.threshold_ms):
            
            self.current_metric.metadata["performance_alert"] = True
            self.current_metric.metadata["threshold_exceeded"] = (
                self.current_metric.duration_ms - self.threshold_ms
            )
        
        return result