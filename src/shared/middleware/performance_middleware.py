# src/shared/middleware/performance_middleware.py
"""
Middleware de performance para monitoramento e otimização.
Inclui métricas de tempo, rate limiting e cache headers.
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time
import asyncio
from datetime import datetime, timedelta

from src.shared.infrastructure.logging_config import get_logger
from src.shared.infrastructure.cache import cache_manager
from src.shared.exceptions.domain_exceptions import RateLimitExceededError

logger = get_logger("performance_middleware")


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Middleware para monitoramento de performance e otimizações."""
    
    def __init__(self, app):
        super().__init__(app)
        self.metrics_cache = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Marcar início do processamento
        start_time = time.time()
        request_start = datetime.utcnow()
        
        # Adicionar informações de timing ao request
        request.state.start_time = start_time
        request.state.request_id = f"{int(start_time * 1000000)}"
        
        # Log da requisição
        logger.info("Request started",
                   request_id=request.state.request_id,
                   method=request.method,
                   path=request.url.path,
                   query_params=str(request.query_params),
                   user_agent=request.headers.get("user-agent", "unknown"))
        
        try:
            # Processar request
            response = await call_next(request)
            
            # Calcular tempo de processamento
            process_time = time.time() - start_time
            
            # Adicionar headers de performance
            response.headers["X-Process-Time"] = str(process_time)
            response.headers["X-Request-ID"] = request.state.request_id
            response.headers["X-Timestamp"] = request_start.isoformat()
            
            # Log da resposta
            logger.info("Request completed",
                       request_id=request.state.request_id,
                       method=request.method,
                       path=request.url.path,
                       status_code=response.status_code,
                       process_time_ms=round(process_time * 1000, 2))
            
            # Registrar métricas
            await self._record_metrics(request, response, process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            logger.error("Request failed",
                        request_id=request.state.request_id,
                        method=request.method,
                        path=request.url.path,
                        error=str(e),
                        process_time_ms=round(process_time * 1000, 2))
            
            raise
    
    async def _record_metrics(self, request: Request, response: Response, process_time: float):
        """Registra métricas de performance."""
        try:
            # Chave para métricas por endpoint
            endpoint_key = f"{request.method}_{request.url.path}"
            
            # Incrementar contador de requests
            await cache_manager.cache.increment(
                "stats:",
                f"requests_{endpoint_key}",
                ttl=3600  # 1 hora
            )
            
            # Registrar tempo de resposta (média móvel)
            await self._update_response_time_metric(endpoint_key, process_time)
            
            # Incrementar contador por status code
            await cache_manager.cache.increment(
                "stats:",
                f"status_{response.status_code}",
                ttl=3600
            )
            
        except Exception as e:
            logger.warning("Error recording metrics", error=str(e))
    
    async def _update_response_time_metric(self, endpoint_key: str, process_time: float):
        """Atualiza métrica de tempo de resposta com média móvel."""
        try:
            # Obter métricas atuais
            current_metrics = await cache_manager.cache.get(
                "stats:",
                f"response_time_{endpoint_key}"
            )
            
            if current_metrics:
                # Calcular nova média (média móvel simples)
                count = current_metrics.get("count", 0)
                avg_time = current_metrics.get("avg_time", 0)
                
                new_count = count + 1
                new_avg = ((avg_time * count) + process_time) / new_count
                
                metrics = {
                    "avg_time": new_avg,
                    "count": new_count,
                    "last_time": process_time,
                    "updated_at": datetime.utcnow().isoformat()
                }
            else:
                # Primeira medição
                metrics = {
                    "avg_time": process_time,
                    "count": 1,
                    "last_time": process_time,
                    "updated_at": datetime.utcnow().isoformat()
                }
            
            # Salvar métricas atualizadas
            await cache_manager.cache.set(
                "stats:",
                f"response_time_{endpoint_key}",
                metrics,
                ttl=3600
            )
            
        except Exception as e:
            logger.warning("Error updating response time metric", error=str(e))


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware de rate limiting usando Redis."""
    
    def __init__(self, app, default_limit: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.default_limit = default_limit
        self.window_seconds = window_seconds
        
        # Rate limits específicos por endpoint
        self.endpoint_limits = {
            "POST_/auth/token": {"limit": 5, "window": 60},  # Login mais restritivo
            "POST_/media/": {"limit": 10, "window": 60},     # Upload de mídia
            "GET_/media/": {"limit": 50, "window": 60},      # Listagem
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Identificar cliente (IP + User ID se autenticado)
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        client_id = f"{client_ip}_{user_id}" if user_id else client_ip
        
        # Obter limites para o endpoint
        endpoint_key = f"{request.method}_{request.url.path}"
        limits = self.endpoint_limits.get(endpoint_key, {
            "limit": self.default_limit,
            "window": self.window_seconds
        })
        
        # Verificar rate limit
        rate_limit_result = await cache_manager.check_rate_limit(
            identifier=f"{endpoint_key}_{client_id}",
            limit=limits["limit"],
            window=limits["window"]
        )
        
        # Se excedeu o limite, retornar erro
        if not rate_limit_result["allowed"]:
            logger.warning("Rate limit exceeded",
                          client_id=client_id,
                          endpoint=endpoint_key,
                          current_count=rate_limit_result["current_count"],
                          limit=limits["limit"])
            
            raise RateLimitExceededError(
                resource=endpoint_key,
                limit=limits["limit"],
                window=f"{limits['window']} seconds"
            )
        
        # Processar request normalmente
        response = await call_next(request)
        
        # Adicionar headers de rate limit
        response.headers["X-RateLimit-Limit"] = str(limits["limit"])
        response.headers["X-RateLimit-Remaining"] = str(rate_limit_result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(rate_limit_result["reset_time"])
        
        return response


class CacheHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para adicionar headers de cache apropriados."""
    
    def __init__(self, app):
        super().__init__(app)
        
        # Configurações de cache por tipo de endpoint
        self.cache_configs = {
            # Recursos estáticos - cache longo
            "static": {"max_age": 86400, "must_revalidate": False},  # 24 horas
            
            # Dados de usuário - cache curto
            "GET_/auth/me": {"max_age": 300, "must_revalidate": True},  # 5 minutos
            
            # Listas de mídia - cache médio
            "GET_/media/": {"max_age": 600, "must_revalidate": True},  # 10 minutos
            
            # Conteúdo processado - cache longo
            "GET_/transcriptions/": {"max_age": 3600, "must_revalidate": False},  # 1 hora
            "GET_/summaries/": {"max_age": 3600, "must_revalidate": False},
            
            # APIs que modificam dados - sem cache
            "POST": {"max_age": 0, "no_cache": True},
            "PUT": {"max_age": 0, "no_cache": True},
            "DELETE": {"max_age": 0, "no_cache": True},
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        
        # Determinar configuração de cache
        endpoint_key = f"{request.method}_{request.url.path}"
        
        # Verificar configuração específica primeiro
        cache_config = self.cache_configs.get(endpoint_key)
        
        # Fallback para configuração por método
        if not cache_config:
            cache_config = self.cache_configs.get(request.method)
        
        # Aplicar headers de cache
        if cache_config:
            if cache_config.get("no_cache"):
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                response.headers["Pragma"] = "no-cache"
                response.headers["Expires"] = "0"
            else:
                max_age = cache_config["max_age"]
                cache_control = f"max-age={max_age}"
                
                if cache_config.get("must_revalidate"):
                    cache_control += ", must-revalidate"
                
                response.headers["Cache-Control"] = cache_control
                
                # Adicionar ETag para validação
                if hasattr(response, "body") and response.body:
                    import hashlib
                    etag = hashlib.md5(response.body).hexdigest()[:16]
                    response.headers["ETag"] = f'"{etag}"'
        
        return response


def register_performance_middleware(app):
    """Registra todos os middlewares de performance."""
    
    # Ordem importa - últimos adicionados são executados primeiro
    app.add_middleware(CacheHeadersMiddleware)
    app.add_middleware(RateLimitMiddleware, default_limit=100, window_seconds=60)
    app.add_middleware(PerformanceMiddleware)
    
    logger.info("Performance middlewares registered successfully")