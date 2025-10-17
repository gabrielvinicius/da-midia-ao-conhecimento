# src/shared/monitoring/business_metrics_collector.py
"""
Business-specific metrics collection - Single Responsibility Principle
Handles domain-specific metrics like media processing, user actions, etc.
"""

from typing import Dict, Optional
from .core_metrics_collector import CoreMetricsCollector, MetricDefinition, MetricType
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("business_metrics")


class BusinessMetricsCollector:
    """
    Business metrics with Single Responsibility:
    Collect and manage domain-specific application metrics
    """
    
    def __init__(self, core_collector: CoreMetricsCollector):
        self.core = core_collector
        self._initialize_business_metrics()
    
    def _initialize_business_metrics(self):
        """Initialize business-specific metrics"""
        
        # Media processing metrics
        self.core.register_custom_metric(MetricDefinition(
            name='media_processing_total',
            metric_type=MetricType.COUNTER,
            description='Total media processing attempts',
            labels=['media_type', 'status', 'provider']
        ))
        
        self.core.register_custom_metric(MetricDefinition(
            name='media_processing_duration_seconds',
            metric_type=MetricType.HISTOGRAM,
            description='Media processing duration',
            labels=['media_type', 'stage'],
            buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0]
        ))
        
        self.core.register_custom_metric(MetricDefinition(
            name='media_file_size_bytes',
            metric_type=MetricType.HISTOGRAM,
            description='Media file size distribution',
            labels=['media_type'],
            buckets=[1024, 1024*1024, 10*1024*1024, 100*1024*1024, 1024*1024*1024]
        ))
        
        # User activity metrics
        self.core.register_custom_metric(MetricDefinition(
            name='user_sessions_total',
            metric_type=MetricType.COUNTER,
            description='Total user sessions',
            labels=['session_type']
        ))
        
        self.core.register_custom_metric(MetricDefinition(
            name='active_users',
            metric_type=MetricType.GAUGE,
            description='Currently active users'
        ))
        
        # Processing pipeline metrics
        self.core.register_custom_metric(MetricDefinition(
            name='pipeline_executions_total',
            metric_type=MetricType.COUNTER,
            description='Total pipeline executions',
            labels=['pipeline_type', 'status']
        ))
        
        logger.info("Business metrics initialized")
    
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
        
        # Processing attempt
        self.core.increment_counter('media_processing_total', {
            'media_type': media_type,
            'status': status,
            'provider': provider
        })
        
        # Processing duration
        self.core.observe_histogram('media_processing_duration_seconds', duration, {
            'media_type': media_type,
            'stage': stage
        })
        
        # File size
        self.core.observe_histogram('media_file_size_bytes', file_size, {
            'media_type': media_type
        })
        
        logger.debug(f"Recorded media processing: {media_type}/{status}/{provider}")
    
    def record_user_session(self, session_type: str = "web"):
        """Record user session start"""
        self.core.increment_counter('user_sessions_total', {
            'session_type': session_type
        })
    
    def update_active_users(self, count: int):
        """Update active users count"""
        self.core.set_gauge('active_users', count)
    
    def record_pipeline_execution(self, pipeline_type: str, status: str):
        """Record pipeline execution"""
        self.core.increment_counter('pipeline_executions_total', {
            'pipeline_type': pipeline_type,
            'status': status
        })
    
    def record_error(self, error_type: str, component: str):
        """Record application error"""
        # Define error metric if not exists
        error_metric_name = 'application_errors_total'
        if not self.core.get_metric(error_metric_name):
            self.core.register_custom_metric(MetricDefinition(
                name=error_metric_name,
                metric_type=MetricType.COUNTER,
                description='Total application errors',
                labels=['error_type', 'component']
            ))
        
        self.core.increment_counter(error_metric_name, {
            'error_type': error_type,
            'component': component
        })


# Default instance
business_metrics = BusinessMetricsCollector(core_metrics)