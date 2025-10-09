# src/shared/monitoring/metrics_collector.py
"""
Sistema avançado de coleta e análise de métricas.
Integração com Prometheus, alertas e dashboards.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import psutil
import json

from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, generate_latest
from prometheus_client.core import CONTENT_TYPE_LATEST

from src.shared.infrastructure.logging_config import get_logger
from src.shared.infrastructure.cache import cache_manager, CacheConfig

logger = get_logger("metrics_collector")


class MetricType(str, Enum):
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class MetricDefinition:
    """Definição de uma métrica personalizada."""
    name: str
    metric_type: MetricType
    description: str
    labels: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # Para histogramas
    registry: Optional[CollectorRegistry] = None


@dataclass
class Alert:
    """Definição de um alerta."""
    name: str
    condition: str  # Expressão de avaliação
    threshold: float
    severity: AlertSeverity
    message: str
    enabled: bool = True
    cooldown_minutes: int = 10


class MetricsCollector:
    """Coletor central de métricas com alertas e dashboards."""
    
    def __init__(self):
        self.registry = CollectorRegistry()
        self.metrics: Dict[str, Any] = {}
        self.alerts: List[Alert] = []
        self.alert_history: Dict[str, datetime] = {}
        
        # Métricas do sistema
        self._setup_system_metrics()
        
        # Métricas da aplicação
        self._setup_application_metrics()
        
        # Alertas padrão
        self._setup_default_alerts()
        
        # Task de coleta periódica
        self._collection_task: Optional[asyncio.Task] = None
    
    def _setup_system_metrics(self):
        """Configura métricas do sistema."""
        
        self.metrics['cpu_usage'] = Gauge(
            'system_cpu_usage_percent',
            'CPU usage percentage',
            registry=self.registry
        )
        
        self.metrics['memory_usage'] = Gauge(
            'system_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=self.registry
        )
        
        self.metrics['disk_usage'] = Gauge(
            'system_disk_usage_bytes',
            'Disk usage in bytes',
            ['mountpoint', 'type'],
            registry=self.registry
        )
        
        self.metrics['network_bytes'] = Counter(
            'system_network_bytes_total',
            'Network bytes transferred',
            ['direction', 'interface'],
            registry=self.registry
        )
    
    def _setup_application_metrics(self):
        """Configura métricas da aplicação."""
        
        # Métricas de requisições HTTP
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
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=self.registry
        )
        
        # Métricas de processamento de mídia
        self.metrics['media_processing'] = Counter(
            'media_processing_total',
            'Total media files processed',
            ['media_type', 'status', 'provider'],
            registry=self.registry
        )
        
        self.metrics['media_processing_duration'] = Histogram(
            'media_processing_duration_seconds',
            'Time spent processing media files',
            ['media_type', 'stage'],
            buckets=[1, 5, 10, 30, 60, 300, 600, 1800],
            registry=self.registry
        )
        
        self.metrics['media_file_size'] = Histogram(
            'media_file_size_bytes',
            'Size of media files',
            ['media_type'],
            buckets=[1024, 10240, 102400, 1048576, 10485760, 104857600, 1073741824],
            registry=self.registry
        )
        
        # Métricas de cache
        self.metrics['cache_operations'] = Counter(
            'cache_operations_total',
            'Total cache operations',
            ['operation', 'cache_type', 'result'],
            registry=self.registry
        )
        
        self.metrics['cache_hit_ratio'] = Gauge(
            'cache_hit_ratio',
            'Cache hit ratio',
            ['cache_type'],
            registry=self.registry
        )
        
        # Métricas de banco de dados
        self.metrics['db_connections'] = Gauge(
            'database_connections_active',
            'Active database connections',
            registry=self.registry
        )
        
        self.metrics['db_query_duration'] = Histogram(
            'database_query_duration_seconds',
            'Database query execution time',
            ['query_type', 'table'],
            buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
            registry=self.registry
        )
        
        # Métricas de usuários
        self.metrics['active_users'] = Gauge(
            'active_users_total',
            'Number of active users',
            ['time_window'],
            registry=self.registry
        )
        
        self.metrics['websocket_connections'] = Gauge(
            'websocket_connections_active',
            'Active WebSocket connections',
            registry=self.registry
        )
    
    def _setup_default_alerts(self):
        """Configura alertas padrão."""
        
        self.alerts = [
            Alert(
                name="high_cpu_usage",
                condition="cpu_usage > threshold",
                threshold=80.0,
                severity=AlertSeverity.MEDIUM,
                message="CPU usage is above 80%"
            ),
            Alert(
                name="high_memory_usage",
                condition="memory_usage_percent > threshold",
                threshold=85.0,
                severity=AlertSeverity.MEDIUM,
                message="Memory usage is above 85%"
            ),
            Alert(
                name="disk_space_low",
                condition="disk_usage_percent > threshold",
                threshold=90.0,
                severity=AlertSeverity.HIGH,
                message="Disk space is above 90%"
            ),
            Alert(
                name="high_error_rate",
                condition="error_rate > threshold",
                threshold=5.0,
                severity=AlertSeverity.HIGH,
                message="HTTP error rate is above 5%",
                cooldown_minutes=5
            ),
            Alert(
                name="slow_response_time",
                condition="avg_response_time > threshold",
                threshold=2.0,
                severity=AlertSeverity.MEDIUM,
                message="Average response time is above 2 seconds"
            ),
            Alert(
                name="media_processing_failures",
                condition="processing_failure_rate > threshold",
                threshold=10.0,
                severity=AlertSeverity.HIGH,
                message="Media processing failure rate is above 10%"
            )
        ]
    
    async def start_collection(self, interval_seconds: int = 30):
        """Inicia coleta periódica de métricas."""
        if self._collection_task and not self._collection_task.done():
            logger.warning("Metrics collection already running")
            return
        
        self._collection_task = asyncio.create_task(
            self._collection_loop(interval_seconds)
        )
        
        logger.info("Metrics collection started", interval_seconds=interval_seconds)
    
    async def stop_collection(self):
        """Para coleta de métricas."""
        if self._collection_task:
            self._collection_task.cancel()
            try:
                await self._collection_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Metrics collection stopped")
    
    async def _collection_loop(self, interval_seconds: int):
        """Loop principal de coleta de métricas."""
        while True:
            try:
                await self._collect_system_metrics()
                await self._collect_application_metrics()
                await self._check_alerts()
                
                # Salvar snapshot no cache
                await self._save_metrics_snapshot()
                
            except Exception as e:
                logger.error("Error in metrics collection", error=str(e))
            
            await asyncio.sleep(interval_seconds)
    
    async def _collect_system_metrics(self):
        """Coleta métricas do sistema."""
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics['cpu_usage'].set(cpu_percent)
            
            # Memória
            memory = psutil.virtual_memory()
            self.metrics['memory_usage'].labels(type='used').set(memory.used)
            self.metrics['memory_usage'].labels(type='available').set(memory.available)
            self.metrics['memory_usage'].labels(type='total').set(memory.total)
            
            # Disco
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    self.metrics['disk_usage'].labels(
                        mountpoint=partition.mountpoint,
                        type='used'
                    ).set(usage.used)
                    self.metrics['disk_usage'].labels(
                        mountpoint=partition.mountpoint,
                        type='free'
                    ).set(usage.free)
                except PermissionError:
                    pass
            
            # Rede
            network = psutil.net_io_counters(pernic=True)
            for interface, stats in network.items():
                self.metrics['network_bytes'].labels(
                    direction='sent',
                    interface=interface
                )._value._value = stats.bytes_sent
                
                self.metrics['network_bytes'].labels(
                    direction='recv',
                    interface=interface
                )._value._value = stats.bytes_recv
            
        except Exception as e:
            logger.error("Error collecting system metrics", error=str(e))
    
    async def _collect_application_metrics(self):
        """Coleta métricas específicas da aplicação."""
        try:
            # Métricas de cache do Redis
            await self._collect_cache_metrics()
            
            # Métricas de usuários ativos
            await self._collect_user_metrics()
            
        except Exception as e:
            logger.error("Error collecting application metrics", error=str(e))
    
    async def _collect_cache_metrics(self):
        """Coleta métricas de cache."""
        try:
            # Simular coleta de estatísticas de cache
            # Em implementação real, obteria do Redis INFO
            cache_stats = {
                'hits': 1000,
                'misses': 100,
                'total_operations': 1100
            }
            
            hit_ratio = cache_stats['hits'] / cache_stats['total_operations'] * 100
            self.metrics['cache_hit_ratio'].labels(cache_type='redis').set(hit_ratio)
            
        except Exception as e:
            logger.error("Error collecting cache metrics", error=str(e))
    
    async def _collect_user_metrics(self):
        """Coleta métricas de usuários."""
        try:
            # Obter usuários ativos das últimas 24h, 1h, etc.
            # Em implementação real, consultaria banco de dados
            
            # Simulação para demonstração
            active_users_24h = 150
            active_users_1h = 25
            
            self.metrics['active_users'].labels(time_window='24h').set(active_users_24h)
            self.metrics['active_users'].labels(time_window='1h').set(active_users_1h)
            
        except Exception as e:
            logger.error("Error collecting user metrics", error=str(e))
    
    async def _check_alerts(self):
        """Verifica condições de alerta."""
        for alert in self.alerts:
            if not alert.enabled:
                continue
            
            # Verificar cooldown
            if alert.name in self.alert_history:
                last_alert = self.alert_history[alert.name]
                cooldown_end = last_alert + timedelta(minutes=alert.cooldown_minutes)
                if datetime.utcnow() < cooldown_end:
                    continue
            
            # Avaliar condição
            try:
                should_alert = await self._evaluate_alert_condition(alert)
                
                if should_alert:
                    await self._trigger_alert(alert)
                    self.alert_history[alert.name] = datetime.utcnow()
                    
            except Exception as e:
                logger.error("Error evaluating alert", 
                           alert_name=alert.name, 
                           error=str(e))
    
    async def _evaluate_alert_condition(self, alert: Alert) -> bool:
        """Avalia condição de um alerta."""
        # Implementação simplificada - em produção usaria parser mais robusto
        
        if alert.condition == "cpu_usage > threshold":
            cpu_value = self.metrics['cpu_usage']._value._value
            return cpu_value > alert.threshold
        
        elif alert.condition == "memory_usage_percent > threshold":
            # Calcular porcentagem de uso de memória
            try:
                memory = psutil.virtual_memory()
                return memory.percent > alert.threshold
            except:
                return False
        
        elif alert.condition == "disk_usage_percent > threshold":
            # Verificar uso de disco para partição principal
            try:
                usage = psutil.disk_usage('/')
                usage_percent = (usage.used / usage.total) * 100
                return usage_percent > alert.threshold
            except:
                return False
        
        # Adicionar mais condições conforme necessário
        return False
    
    async def _trigger_alert(self, alert: Alert):
        """Dispara um alerta."""
        alert_data = {
            "name": alert.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "threshold": alert.threshold,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Log do alerta
        logger.warning("Alert triggered", **alert_data)
        
        # Salvar no cache para dashboard
        await cache_manager.cache.set(
            CacheConfig.PREFIXES["stats"],
            f"alert_{alert.name}_{int(time.time())}",
            alert_data,
            CacheConfig.EXTENDED_TTL
        )
        
        # Em produção, enviaria para sistemas de notificação
        # (Slack, email, PagerDuty, etc.)
    
    async def _save_metrics_snapshot(self):
        """Salva snapshot atual das métricas."""
        try:
            snapshot = {
                "timestamp": datetime.utcnow().isoformat(),
                "system": {
                    "cpu_usage": getattr(self.metrics['cpu_usage']._value, '_value', 0),
                    "memory_usage_percent": psutil.virtual_memory().percent,
                    "disk_usage_percent": (psutil.disk_usage('/').used / psutil.disk_usage('/').total) * 100
                },
                "application": {
                    "active_connections": 0,  # Implementar conforme necessário
                }
            }
            
            await cache_manager.cache.set(
                CacheConfig.PREFIXES["stats"],
                "metrics_snapshot",
                snapshot,
                CacheConfig.SHORT_TTL
            )
            
        except Exception as e:
            logger.error("Error saving metrics snapshot", error=str(e))
    
    # === Métodos públicos para instrumentação ===
    
    def record_http_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Registra métrica de requisição HTTP."""
        self.metrics['http_requests'].labels(
            method=method,
            endpoint=endpoint,
            status_code=str(status_code)
        ).inc()
        
        self.metrics['http_request_duration'].labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def record_media_processing(
        self, 
        media_type: str, 
        status: str, 
        provider: str, 
        duration: float,
        stage: str,
        file_size: int
    ):
        """Registra métrica de processamento de mídia."""
        self.metrics['media_processing'].labels(
            media_type=media_type,
            status=status,
            provider=provider
        ).inc()
        
        self.metrics['media_processing_duration'].labels(
            media_type=media_type,
            stage=stage
        ).observe(duration)
        
        self.metrics['media_file_size'].labels(
            media_type=media_type
        ).observe(file_size)
    
    def record_cache_operation(self, operation: str, cache_type: str, result: str):
        """Registra operação de cache."""
        self.metrics['cache_operations'].labels(
            operation=operation,
            cache_type=cache_type,
            result=result
        ).inc()
    
    def record_db_query(self, query_type: str, table: str, duration: float):
        """Registra consulta de banco de dados."""
        self.metrics['db_query_duration'].labels(
            query_type=query_type,
            table=table
        ).observe(duration)
    
    def set_websocket_connections(self, count: int):
        """Define número de conexões WebSocket ativas."""
        self.metrics['websocket_connections'].set(count)
    
    def set_db_connections(self, count: int):
        """Define número de conexões de banco ativas."""
        self.metrics['db_connections'].set(count)
    
    # === Métodos para exposição de métricas ===
    
    def get_prometheus_metrics(self) -> str:
        """Retorna métricas no formato Prometheus."""
        return generate_latest(self.registry).decode('utf-8')
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Retorna dados para dashboard."""
        try:
            # Obter snapshot atual
            snapshot = await cache_manager.cache.get(
                CacheConfig.PREFIXES["stats"],
                "metrics_snapshot"
            )
            
            # Obter alertas recentes
            recent_alerts = []
            # Em implementação real, buscaria alertas do cache
            
            # Obter métricas agregadas
            dashboard_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "system": snapshot.get("system", {}) if snapshot else {},
                "application": snapshot.get("application", {}) if snapshot else {},
                "alerts": recent_alerts,
                "status": "healthy"  # Implementar lógica de status
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error("Error getting dashboard data", error=str(e))
            return {"error": str(e)}


# Instância global
metrics_collector = MetricsCollector()