# src/shared/monitoring/system_metrics_collector.py
"""
System metrics collection - Single Responsibility Principle
Handles OS-level metrics: CPU, memory, disk, network
"""

import asyncio
import psutil
from typing import Dict, Optional
from .core_metrics_collector import CoreMetricsCollector, MetricDefinition, MetricType
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("system_metrics")


class SystemMetricsCollector:
    """
    System metrics with Single Responsibility:
    Collect and monitor OS-level system metrics
    """
    
    def __init__(self, core_collector: CoreMetricsCollector):
        self.core = core_collector
        self._collection_task: Optional[asyncio.Task] = None
        self._initialize_system_metrics()
    
    def _initialize_system_metrics(self):
        """Initialize system-level metrics"""
        
        # Memory metrics
        self.core.register_custom_metric(MetricDefinition(
            name='system_memory_usage_bytes',
            metric_type=MetricType.GAUGE,
            description='Memory usage in bytes',
            labels=['type']
        ))
        
        # Disk metrics
        self.core.register_custom_metric(MetricDefinition(
            name='system_disk_usage_bytes',
            metric_type=MetricType.GAUGE,
            description='Disk usage in bytes',
            labels=['mountpoint', 'type']
        ))
        
        # Network metrics
        self.core.register_custom_metric(MetricDefinition(
            name='system_network_bytes_total',
            metric_type=MetricType.COUNTER,
            description='Network bytes transferred',
            labels=['direction', 'interface']
        ))
        
        logger.info("System metrics initialized")
    
    async def collect_system_metrics(self):
        """Collect all system metrics"""
        try:
            await self._collect_cpu_metrics()
            await self._collect_memory_metrics()
            await self._collect_disk_metrics()
            await self._collect_network_metrics()
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    async def _collect_cpu_metrics(self):
        """Collect CPU metrics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            self.core.set_gauge('cpu_usage', cpu_percent)
            
        except Exception as e:
            logger.error(f"Error collecting CPU metrics: {e}")
    
    async def _collect_memory_metrics(self):
        """Collect memory metrics"""
        try:
            memory = psutil.virtual_memory()
            
            self.core.set_gauge('system_memory_usage_bytes', memory.used, {'type': 'used'})
            self.core.set_gauge('system_memory_usage_bytes', memory.available, {'type': 'available'})
            self.core.set_gauge('system_memory_usage_bytes', memory.total, {'type': 'total'})
            
        except Exception as e:
            logger.error(f"Error collecting memory metrics: {e}")
    
    async def _collect_disk_metrics(self):
        """Collect disk metrics"""
        try:
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    self.core.set_gauge('system_disk_usage_bytes', usage.used, {
                        'mountpoint': partition.mountpoint,
                        'type': 'used'
                    })
                    self.core.set_gauge('system_disk_usage_bytes', usage.free, {
                        'mountpoint': partition.mountpoint,
                        'type': 'free'
                    })
                    
                except (PermissionError, OSError):
                    # Skip inaccessible partitions
                    continue
                    
        except Exception as e:
            logger.error(f"Error collecting disk metrics: {e}")
    
    async def _collect_network_metrics(self):
        """Collect network metrics"""
        try:
            network = psutil.net_io_counters(pernic=True)
            
            for interface, stats in network.items():
                # Note: For Counter metrics, we would need to track deltas
                # This is a simplified implementation
                pass
                
        except Exception as e:
            logger.error(f"Error collecting network metrics: {e}")
    
    async def start_collection(self, interval_seconds: int = 30):
        """Start periodic system metrics collection"""
        if self._collection_task and not self._collection_task.done():
            logger.warning("System metrics collection already running")
            return
        
        self._collection_task = asyncio.create_task(
            self._collection_loop(interval_seconds)
        )
        
        logger.info(f"System metrics collection started (interval: {interval_seconds}s)")
    
    async def stop_collection(self):
        """Stop system metrics collection"""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("System metrics collection stopped")
    
    async def _collection_loop(self, interval_seconds: int):
        """Main collection loop"""
        while True:
            try:
                await self.collect_system_metrics()
                await asyncio.sleep(interval_seconds)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in system metrics collection loop: {e}")
                await asyncio.sleep(interval_seconds)


# Default instance
system_metrics = SystemMetricsCollector(core_metrics)