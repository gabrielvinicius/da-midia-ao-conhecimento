"""
Analytics Visitors using Visitor Pattern for data analysis operations
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

from src.shared.patterns.visitor import (
    BaseVisitor, IVisitable, LeafElement, CompositeElement, 
    VisitorResult, VisitorRegistry
)


@dataclass
class MetricData:
    """Data structure for metrics"""
    name: str
    value: float
    timestamp: datetime
    category: str = "general"
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


@dataclass 
class UserActivity:
    """Data structure for user activity"""
    user_id: str
    action: str
    timestamp: datetime
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class SystemEvent:
    """Data structure for system events"""
    event_type: str
    severity: str
    timestamp: datetime
    component: str
    message: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class MetricElement(LeafElement):
    """Visitable element for metrics"""
    
    def __init__(self, metric: MetricData):
        super().__init__(f"Metric_{metric.name}", metric)
        self.metric = metric
    
    def get_element_type(self) -> str:
        return "Metric"


class UserActivityElement(LeafElement):
    """Visitable element for user activities"""
    
    def __init__(self, activity: UserActivity):
        super().__init__(f"Activity_{activity.action}", activity)
        self.activity = activity
    
    def get_element_type(self) -> str:
        return "UserActivity"


class SystemEventElement(LeafElement):
    """Visitable element for system events"""
    
    def __init__(self, event: SystemEvent):
        super().__init__(f"Event_{event.event_type}", event)
        self.event = event
    
    def get_element_type(self) -> str:
        return "SystemEvent"


class AnalyticsDataContainer(CompositeElement):
    """Container for analytics data elements"""
    
    def __init__(self, name: str, time_range: tuple = None):
        super().__init__(name)
        self.time_range = time_range
        self.metrics: List[MetricElement] = []
        self.activities: List[UserActivityElement] = []
        self.events: List[SystemEventElement] = []
    
    def add_metric(self, metric: MetricData) -> None:
        """Add metric to container"""
        element = MetricElement(metric)
        self.add_child(element)
        self.metrics.append(element)
    
    def add_activity(self, activity: UserActivity) -> None:
        """Add user activity to container"""
        element = UserActivityElement(activity)
        self.add_child(element)
        self.activities.append(element)
    
    def add_event(self, event: SystemEvent) -> None:
        """Add system event to container"""
        element = SystemEventElement(event)
        self.add_child(element)
        self.events.append(element)
    
    def get_element_type(self) -> str:
        return "AnalyticsDataContainer"


class StatisticsVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for calculating statistical analysis"""
    
    def __init__(self):
        super().__init__("StatisticsVisitor")
        self.metric_values = defaultdict(list)
        self.activity_counts = defaultdict(int)
        self.event_counts = defaultdict(int)
    
    def visit_Metric(self, element: MetricElement) -> Dict[str, Any]:
        """Visit metric element and collect values"""
        metric = element.metric
        
        # Collect values by category
        self.metric_values[metric.category].append(metric.value)
        self.metric_values[f"{metric.category}_{metric.name}"].append(metric.value)
        
        self.result.add_result(f"metric_{metric.name}", metric.value)
        
        return {
            "type": "metric",
            "name": metric.name,
            "value": metric.value,
            "category": metric.category
        }
    
    def visit_UserActivity(self, element: UserActivityElement) -> Dict[str, Any]:
        """Visit user activity element"""
        activity = element.activity
        
        # Count activities by type
        self.activity_counts[activity.action] += 1
        self.activity_counts[f"user_{activity.user_id}"] += 1
        
        return {
            "type": "activity",
            "action": activity.action,
            "user_id": activity.user_id,
            "timestamp": activity.timestamp.isoformat()
        }
    
    def visit_SystemEvent(self, element: SystemEventElement) -> Dict[str, Any]:
        """Visit system event element"""
        event = element.event
        
        # Count events by type and severity
        self.event_counts[event.event_type] += 1
        self.event_counts[f"severity_{event.severity}"] += 1
        self.event_counts[f"component_{event.component}"] += 1
        
        return {
            "type": "event",
            "event_type": event.event_type,
            "severity": event.severity,
            "component": event.component
        }
    
    def visit_AnalyticsDataContainer(self, element: AnalyticsDataContainer) -> Dict[str, Any]:
        """Visit analytics container and provide summary"""
        return {
            "type": "container",
            "name": element.name,
            "metrics_count": len(element.metrics),
            "activities_count": len(element.activities),
            "events_count": len(element.events),
            "total_elements": len(element.children)
        }
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        """Default result for unknown elements"""
        return {
            "type": "unknown",
            "element_type": element.get_element_type()
        }
    
    def get_statistics_summary(self) -> Dict[str, Any]:
        """Get comprehensive statistics summary"""
        
        # Calculate metric statistics
        metric_stats = {}
        for category, values in self.metric_values.items():
            if values:
                metric_stats[category] = {
                    "count": len(values),
                    "sum": sum(values),
                    "mean": statistics.mean(values),
                    "median": statistics.median(values),
                    "min": min(values),
                    "max": max(values),
                    "stdev": statistics.stdev(values) if len(values) > 1 else 0
                }
        
        return {
            "metric_statistics": metric_stats,
            "activity_counts": dict(self.activity_counts),
            "event_counts": dict(self.event_counts),
            "total_visited": self.result.visited_count
        }


class TrendAnalysisVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for trend analysis over time"""
    
    def __init__(self, time_window_hours: int = 24):
        super().__init__("TrendAnalysisVisitor")
        self.time_window_hours = time_window_hours
        self.time_series_data = defaultdict(list)
        self.current_time = datetime.now()
    
    def visit_Metric(self, element: MetricElement) -> Dict[str, Any]:
        """Analyze metric trends"""
        metric = element.metric
        
        # Only consider recent data within time window
        if self._is_within_time_window(metric.timestamp):
            time_bucket = self._get_time_bucket(metric.timestamp)
            self.time_series_data[f"metric_{metric.name}"].append({
                "timestamp": metric.timestamp,
                "value": metric.value,
                "bucket": time_bucket
            })
        
        return {
            "type": "metric_trend",
            "name": metric.name,
            "timestamp": metric.timestamp.isoformat(),
            "within_window": self._is_within_time_window(metric.timestamp)
        }
    
    def visit_UserActivity(self, element: UserActivityElement) -> Dict[str, Any]:
        """Analyze activity trends"""
        activity = element.activity
        
        if self._is_within_time_window(activity.timestamp):
            time_bucket = self._get_time_bucket(activity.timestamp)
            self.time_series_data[f"activity_{activity.action}"].append({
                "timestamp": activity.timestamp,
                "user_id": activity.user_id,
                "bucket": time_bucket
            })
        
        return {
            "type": "activity_trend",
            "action": activity.action,
            "timestamp": activity.timestamp.isoformat()
        }
    
    def visit_SystemEvent(self, element: SystemEventElement) -> Dict[str, Any]:
        """Analyze event trends"""
        event = element.event
        
        if self._is_within_time_window(event.timestamp):
            time_bucket = self._get_time_bucket(event.timestamp)
            self.time_series_data[f"event_{event.event_type}"].append({
                "timestamp": event.timestamp,
                "severity": event.severity,
                "bucket": time_bucket
            })
        
        return {
            "type": "event_trend",
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat()
        }
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "trend_unknown"}
    
    def _is_within_time_window(self, timestamp: datetime) -> bool:
        """Check if timestamp is within analysis window"""
        time_diff = self.current_time - timestamp
        return time_diff <= timedelta(hours=self.time_window_hours)
    
    def _get_time_bucket(self, timestamp: datetime, bucket_minutes: int = 60) -> str:
        """Get time bucket for grouping"""
        # Round to nearest hour by default
        rounded_time = timestamp.replace(minute=0, second=0, microsecond=0)
        return rounded_time.isoformat()
    
    def get_trend_analysis(self) -> Dict[str, Any]:
        """Get trend analysis results"""
        
        trend_results = {}
        
        for series_name, data_points in self.time_series_data.items():
            if len(data_points) < 2:
                continue
            
            # Group by time buckets
            bucket_counts = defaultdict(int)
            bucket_values = defaultdict(list)
            
            for point in data_points:
                bucket = point["bucket"]
                bucket_counts[bucket] += 1
                
                if "value" in point:
                    bucket_values[bucket].append(point["value"])
            
            # Calculate trend
            sorted_buckets = sorted(bucket_counts.keys())
            if len(sorted_buckets) >= 2:
                first_half_avg = sum(bucket_counts[b] for b in sorted_buckets[:len(sorted_buckets)//2])
                second_half_avg = sum(bucket_counts[b] for b in sorted_buckets[len(sorted_buckets)//2:])
                
                trend_direction = "increasing" if second_half_avg > first_half_avg else "decreasing"
                if abs(second_half_avg - first_half_avg) < 0.1 * first_half_avg:
                    trend_direction = "stable"
                
                trend_results[series_name] = {
                    "data_points": len(data_points),
                    "time_buckets": len(bucket_counts),
                    "trend_direction": trend_direction,
                    "first_half_avg": first_half_avg,
                    "second_half_avg": second_half_avg,
                    "bucket_data": dict(bucket_counts)
                }
        
        return trend_results


class AnomalyDetectionVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for detecting anomalies in data"""
    
    def __init__(self, threshold_std_dev: float = 2.0):
        super().__init__("AnomalyDetectionVisitor")
        self.threshold_std_dev = threshold_std_dev
        self.metric_baselines = {}
        self.anomalies = []
    
    def visit_Metric(self, element: MetricElement) -> Dict[str, Any]:
        """Detect metric anomalies"""
        metric = element.metric
        baseline_key = f"{metric.category}_{metric.name}"
        
        # Initialize baseline if not exists
        if baseline_key not in self.metric_baselines:
            self.metric_baselines[baseline_key] = []
        
        baseline_values = self.metric_baselines[baseline_key]
        
        # Check for anomaly if we have enough baseline data
        is_anomaly = False
        anomaly_score = 0.0
        
        if len(baseline_values) >= 5:  # Need at least 5 points for baseline
            baseline_mean = statistics.mean(baseline_values)
            baseline_std = statistics.stdev(baseline_values) if len(baseline_values) > 1 else 0
            
            if baseline_std > 0:
                z_score = abs(metric.value - baseline_mean) / baseline_std
                is_anomaly = z_score > self.threshold_std_dev
                anomaly_score = z_score
        
        # Add to baseline (rolling window of last 20 values)
        baseline_values.append(metric.value)
        if len(baseline_values) > 20:
            baseline_values.pop(0)
        
        # Record anomaly
        if is_anomaly:
            anomaly = {
                "type": "metric_anomaly",
                "metric_name": metric.name,
                "value": metric.value,
                "baseline_mean": baseline_mean,
                "anomaly_score": anomaly_score,
                "timestamp": metric.timestamp.isoformat()
            }
            self.anomalies.append(anomaly)
            self.result.add_result(f"anomaly_{len(self.anomalies)}", anomaly)
        
        return {
            "type": "metric_anomaly_check",
            "name": metric.name,
            "value": metric.value,
            "is_anomaly": is_anomaly,
            "anomaly_score": anomaly_score
        }
    
    def visit_UserActivity(self, element: UserActivityElement) -> Dict[str, Any]:
        """Detect activity anomalies (e.g., unusual activity patterns)"""
        activity = element.activity
        
        # Simple anomaly detection: unusual activity times
        hour = activity.timestamp.hour
        is_unusual_time = hour < 6 or hour > 22  # Outside normal hours
        
        if is_unusual_time:
            anomaly = {
                "type": "activity_anomaly",
                "user_id": activity.user_id,
                "action": activity.action,
                "timestamp": activity.timestamp.isoformat(),
                "reason": "unusual_time"
            }
            self.anomalies.append(anomaly)
        
        return {
            "type": "activity_anomaly_check",
            "action": activity.action,
            "is_unusual_time": is_unusual_time
        }
    
    def visit_SystemEvent(self, element: SystemEventElement) -> Dict[str, Any]:
        """Detect event anomalies"""
        event = element.event
        
        # Detect high severity events as anomalies
        is_critical = event.severity.lower() in ["critical", "error", "fatal"]
        
        if is_critical:
            anomaly = {
                "type": "event_anomaly",
                "event_type": event.event_type,
                "severity": event.severity,
                "component": event.component,
                "message": event.message,
                "timestamp": event.timestamp.isoformat()
            }
            self.anomalies.append(anomaly)
        
        return {
            "type": "event_anomaly_check",
            "event_type": event.event_type,
            "is_critical": is_critical
        }
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "anomaly_unknown"}
    
    def get_anomaly_report(self) -> Dict[str, Any]:
        """Get comprehensive anomaly report"""
        
        # Group anomalies by type
        anomaly_groups = defaultdict(list)
        for anomaly in self.anomalies:
            anomaly_groups[anomaly["type"]].append(anomaly)
        
        return {
            "total_anomalies": len(self.anomalies),
            "anomaly_types": dict(anomaly_groups),
            "anomaly_summary": {
                "metric_anomalies": len(anomaly_groups["metric_anomaly"]),
                "activity_anomalies": len(anomaly_groups["activity_anomaly"]), 
                "event_anomalies": len(anomaly_groups["event_anomaly"])
            },
            "recent_anomalies": self.anomalies[-10:] if self.anomalies else []
        }


class ReportGenerationVisitor(BaseVisitor[Dict[str, Any]]):
    """Visitor for generating comprehensive reports"""
    
    def __init__(self, report_type: str = "comprehensive"):
        super().__init__("ReportGenerationVisitor")
        self.report_type = report_type
        self.report_sections = {}
        self.summary_data = defaultdict(int)
    
    def visit_Metric(self, element: MetricElement) -> Dict[str, Any]:
        """Generate metric report section"""
        metric = element.metric
        
        if "metrics" not in self.report_sections:
            self.report_sections["metrics"] = []
        
        metric_report = {
            "name": metric.name,
            "value": metric.value,
            "category": metric.category,
            "timestamp": metric.timestamp.isoformat(),
            "tags": metric.tags
        }
        
        self.report_sections["metrics"].append(metric_report)
        self.summary_data["total_metrics"] += 1
        self.summary_data[f"metrics_{metric.category}"] += 1
        
        return metric_report
    
    def visit_UserActivity(self, element: UserActivityElement) -> Dict[str, Any]:
        """Generate activity report section"""
        activity = element.activity
        
        if "activities" not in self.report_sections:
            self.report_sections["activities"] = []
        
        activity_report = {
            "user_id": activity.user_id,
            "action": activity.action,
            "timestamp": activity.timestamp.isoformat(),
            "metadata": activity.metadata
        }
        
        self.report_sections["activities"].append(activity_report)
        self.summary_data["total_activities"] += 1
        self.summary_data[f"activities_{activity.action}"] += 1
        
        return activity_report
    
    def visit_SystemEvent(self, element: SystemEventElement) -> Dict[str, Any]:
        """Generate event report section"""
        event = element.event
        
        if "events" not in self.report_sections:
            self.report_sections["events"] = []
        
        event_report = {
            "event_type": event.event_type,
            "severity": event.severity,
            "component": event.component,
            "message": event.message,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata
        }
        
        self.report_sections["events"].append(event_report)
        self.summary_data["total_events"] += 1
        self.summary_data[f"events_{event.severity}"] += 1
        
        return event_report
    
    def visit_AnalyticsDataContainer(self, element: AnalyticsDataContainer) -> Dict[str, Any]:
        """Generate container report section"""
        container_report = {
            "name": element.name,
            "time_range": element.time_range,
            "metrics_count": len(element.metrics),
            "activities_count": len(element.activities),
            "events_count": len(element.events)
        }
        
        self.report_sections["container_info"] = container_report
        return container_report
    
    def _create_default_result(self, element: IVisitable) -> Dict[str, Any]:
        return {"type": "report_unknown"}
    
    def generate_final_report(self) -> Dict[str, Any]:
        """Generate final comprehensive report"""
        
        report = {
            "report_type": self.report_type,
            "generated_at": datetime.now().isoformat(),
            "summary": dict(self.summary_data),
            "sections": self.report_sections,
            "metadata": {
                "total_elements_processed": self.result.visited_count,
                "sections_generated": len(self.report_sections),
                "processing_errors": len(self.result.errors)
            }
        }
        
        # Add executive summary for comprehensive reports
        if self.report_type == "comprehensive":
            report["executive_summary"] = self._generate_executive_summary()
        
        return report
    
    def _generate_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary"""
        return {
            "key_findings": [
                f"Processed {self.summary_data['total_metrics']} metrics",
                f"Analyzed {self.summary_data['total_activities']} user activities", 
                f"Reviewed {self.summary_data['total_events']} system events"
            ],
            "recommendations": [
                "Continue monitoring key performance indicators",
                "Investigate any anomalies detected",
                "Review system events for optimization opportunities"
            ]
        }


# Register visitors in the registry
def register_analytics_visitors():
    """Register all analytics visitors"""
    
    VisitorRegistry.register_visitor(
        "statistics_visitor",
        StatisticsVisitor,
        "analytics"
    )
    
    VisitorRegistry.register_visitor(
        "trend_analysis_visitor", 
        TrendAnalysisVisitor,
        "analytics"
    )
    
    VisitorRegistry.register_visitor(
        "anomaly_detection_visitor",
        AnomalyDetectionVisitor, 
        "analytics"
    )
    
    VisitorRegistry.register_visitor(
        "report_generation_visitor",
        ReportGenerationVisitor,
        "analytics"
    )