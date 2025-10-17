# src/shared/monitoring/metrics_alerts.py
"""
Metrics alerting system - Single Responsibility Principle
Handles alert definitions, evaluation, and notifications
"""

import asyncio
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .core_metrics_collector import CoreMetricsCollector
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("metrics_alerts")


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert definition"""
    name: str
    condition: str  # Simple condition like "cpu_usage > 80"
    threshold: float
    severity: AlertSeverity
    message: str
    enabled: bool = True
    cooldown_minutes: int = 10


@dataclass
class AlertEvent:
    """Alert event when condition is met"""
    alert_name: str
    severity: AlertSeverity
    message: str
    metric_value: float
    threshold: float
    timestamp: datetime


class MetricsAlerting:
    """
    Metrics alerting with Single Responsibility:
    Evaluate alert conditions and trigger notifications
    """
    
    def __init__(self, core_collector: CoreMetricsCollector):
        self.core = core_collector
        self.alerts: List[Alert] = []
        self.alert_history: Dict[str, datetime] = {}
        self.notification_handlers: List[Callable[[AlertEvent], None]] = []
        self._monitoring_task: Optional[asyncio.Task] = None
        
        self._setup_default_alerts()
    
    def _setup_default_alerts(self):
        """Setup default system alerts"""
        
        default_alerts = [
            Alert(
                name="high_cpu_usage",
                condition="cpu_usage > 80",
                threshold=80.0,
                severity=AlertSeverity.HIGH,
                message="CPU usage is above 80%"
            ),
            Alert(
                name="critical_cpu_usage", 
                condition="cpu_usage > 95",
                threshold=95.0,
                severity=AlertSeverity.CRITICAL,
                message="CPU usage is critically high (>95%)"
            ),
            Alert(
                name="high_memory_usage",
                condition="memory_usage > 85",
                threshold=85.0,
                severity=AlertSeverity.HIGH,
                message="Memory usage is above 85%"
            ),
        ]
        
        for alert in default_alerts:
            self.add_alert(alert)
        
        logger.info(f"Initialized {len(default_alerts)} default alerts")
    
    def add_alert(self, alert: Alert):
        """Add new alert"""
        self.alerts.append(alert)
        logger.info(f"Added alert: {alert.name}")
    
    def remove_alert(self, alert_name: str) -> bool:
        """Remove alert by name"""
        for i, alert in enumerate(self.alerts):
            if alert.name == alert_name:
                del self.alerts[i]
                logger.info(f"Removed alert: {alert_name}")
                return True
        return False
    
    def enable_alert(self, alert_name: str, enabled: bool = True):
        """Enable/disable alert"""
        for alert in self.alerts:
            if alert.name == alert_name:
                alert.enabled = enabled
                logger.info(f"Alert {alert_name} {'enabled' if enabled else 'disabled'}")
                return
    
    def add_notification_handler(self, handler: Callable[[AlertEvent], None]):
        """Add notification handler for alerts"""
        self.notification_handlers.append(handler)
        logger.info("Added notification handler")
    
    async def check_alerts(self):
        """Check all alert conditions"""
        current_time = datetime.utcnow()
        
        for alert in self.alerts:
            if not alert.enabled:
                continue
            
            # Check cooldown
            last_triggered = self.alert_history.get(alert.name)
            if last_triggered:
                cooldown_end = last_triggered + timedelta(minutes=alert.cooldown_minutes)
                if current_time < cooldown_end:
                    continue
            
            # Evaluate condition
            if await self._evaluate_alert_condition(alert):
                await self._trigger_alert(alert, current_time)
    
    async def _evaluate_alert_condition(self, alert: Alert) -> bool:
        """Evaluate if alert condition is met"""
        try:
            # Simple condition evaluation
            # In production, would use a proper expression evaluator
            
            if "cpu_usage >" in alert.condition:
                cpu_metric = self.core.get_metric('cpu_usage')
                if cpu_metric:
                    current_value = getattr(cpu_metric, '_value', {}).get('_value', 0)
                    return current_value > alert.threshold
            
            elif "memory_usage >" in alert.condition:
                # Simplified memory check
                import psutil
                memory_percent = psutil.virtual_memory().percent
                return memory_percent > alert.threshold
            
            return False
            
        except Exception as e:
            logger.error(f"Error evaluating alert condition {alert.name}: {e}")
            return False
    
    async def _trigger_alert(self, alert: Alert, timestamp: datetime):
        """Trigger alert and send notifications"""
        
        # Get current metric value for context
        metric_value = 0.0
        try:
            if "cpu_usage" in alert.condition:
                cpu_metric = self.core.get_metric('cpu_usage')
                if cpu_metric:
                    metric_value = getattr(cpu_metric, '_value', {}).get('_value', 0)
        except:
            pass
        
        # Create alert event
        alert_event = AlertEvent(
            alert_name=alert.name,
            severity=alert.severity,
            message=alert.message,
            metric_value=metric_value,
            threshold=alert.threshold,
            timestamp=timestamp
        )
        
        # Update history
        self.alert_history[alert.name] = timestamp
        
        # Log alert
        logger.warning(
            f"ALERT TRIGGERED: {alert.name}",
            extra={
                "alert_name": alert.name,
                "severity": alert.severity.value,
                "metric_value": metric_value,
                "threshold": alert.threshold
            }
        )
        
        # Send notifications
        for handler in self.notification_handlers:
            try:
                handler(alert_event)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")
    
    async def start_monitoring(self, check_interval_seconds: int = 60):
        """Start alert monitoring"""
        if self._monitoring_task and not self._monitoring_task.done():
            logger.warning("Alert monitoring already running")
            return
        
        self._monitoring_task = asyncio.create_task(
            self._monitoring_loop(check_interval_seconds)
        )
        
        logger.info(f"Alert monitoring started (interval: {check_interval_seconds}s)")
    
    async def stop_monitoring(self):
        """Stop alert monitoring"""
        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Alert monitoring stopped")
    
    async def _monitoring_loop(self, interval_seconds: int):
        """Main monitoring loop"""
        while True:
            try:
                await self.check_alerts()
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
                await asyncio.sleep(interval_seconds)
    
    def get_alert_status(self) -> Dict[str, Any]:
        """Get current alert status"""
        return {
            "total_alerts": len(self.alerts),
            "enabled_alerts": len([a for a in self.alerts if a.enabled]),
            "recent_triggers": len([
                name for name, time in self.alert_history.items()
                if datetime.utcnow() - time < timedelta(hours=1)
            ]),
            "notification_handlers": len(self.notification_handlers)
        }


# Default notification handler
def default_alert_handler(alert_event: AlertEvent):
    """Default alert notification handler"""
    print(f"🚨 ALERT: {alert_event.alert_name}")
    print(f"   Severity: {alert_event.severity.value.upper()}")
    print(f"   Message: {alert_event.message}")
    print(f"   Value: {alert_event.metric_value} (threshold: {alert_event.threshold})")
    print(f"   Time: {alert_event.timestamp}")


# Default instance
metrics_alerting = MetricsAlerting(core_metrics)
metrics_alerting.add_notification_handler(default_alert_handler)