# src/shared/infrastructure/cache.py
"""Sistema de cache Redis inteligente com múltiplas estratégias.
Suporte a TTL, invalidação automática e cache distribuído.
"""

import json
import pickle
import time
from typing import Any, Dict, Optional

import redis.asyncio as aioredis

from src.shared.infrastructure.settings import settings
from src.shared.infrastructure.logging import get_logger

logger = get_logger("cache")


class CacheConfig:
    """Configurações de cache para diferentes tipos de dados."""

    # TTL padrão para diferentes tipos de dados (em segundos)
    DEFAULT_TTL = 300  # 5 minutos
    SHORT_TTL = 60     # 1 minuto
    MEDIUM_TTL = 900   # 15 minutos
    LONG_TTL = 3600    # 1 hora
    EXTENDED_TTL = 86400  # 24 horas

    # Prefixos para diferentes namespaces
    PREFIXES = {
        "user": "user:",
        "media": "media:",
        "transcription": "transcription:",
        "summary": "summary:",
        "sentiment": "sentiment:",
        "topic": "topic:",
        "stats": "stats:",
        "api_response": "api:",
        "session": "session:"
    }


class RedisCache:
    """Cliente Redis assíncrono otimizado para cache distribuído."""

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.is_connected = False

    async def connect(self):
        """Conecta ao Redis com retry automático."""
        if self.is_connected:
            return

        try:
            self.redis_client = aioredis.from_url(
                settings.redis_url,
                decode_responses=False,  # Para suportar binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                max_connections=20
            )

            # Testar conexão
            await self.redis_client.ping()
            self.is_connected = True

            logger.info("Redis cache connected successfully", url=settings.redis_url)

        except Exception as e:
            logger.error("Failed to connect to Redis cache", extra={"error": str(e)})
            self.is_connected = False
            raise

    async def disconnect(self):
        """Desconecta do Redis."""
        if self.redis_client:
            await self.redis_client.aclose()
            self.is_connected = False
            logger.info("Redis cache disconnected")

    def _generate_key(self, prefix: str, key: str, **kwargs) -> str:
        """Gera chave de cache padronizada."""
        base_key = f"{prefix}{key}"

        # Adicionar parâmetros extras se fornecidos
        if kwargs:
            # Ordenar kwargs para consistência
            sorted_params = sorted(kwargs.items())
            params_str = "&".join(f"{k}={v}" for k, v in sorted_params)
            base_key = f"{base_key}?{params_str}"

        return base_key

    def _serialize_value(self, value: Any) -> bytes:
        """Serializa valor para armazenamento no Redis."""
        if isinstance(value, (str, int, float, bool)):
            return json.dumps(value).encode('utf-8')
        else:
            return pickle.dumps(value)

    def _deserialize_value(self, data: bytes) -> Any:
        """Deserializa valor do Redis."""
        try:
            # Tentar JSON primeiro (mais rápido)
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback para pickle
            return pickle.loads(data)

    async def get(self, prefix: str, key: str, **kwargs) -> Optional[Any]:
        """Obtém valor do cache."""
        if not self.is_connected:
            await self.connect()

        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            data = await self.redis_client.get(cache_key)
            if data is None:
                logger.debug("Cache miss", key=cache_key)
                return None

            value = self._deserialize_value(data)
            logger.debug("Cache hit", key=cache_key)
            return value

        except Exception as e:
            logger.warning("Cache get error", key=cache_key, error=str(e))
            return None

    async def set(
        self,
        prefix: str,
        key: str,
        value: Any,
        ttl: int = CacheConfig.DEFAULT_TTL,
        **kwargs
    ) -> bool:
        """Define valor no cache."""
        if not self.is_connected:
            await self.connect()

        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            serialized_value = self._serialize_value(value)
            await self.redis_client.setex(cache_key, ttl, serialized_value)

            logger.debug("Cache set", key=cache_key, ttl=ttl)
            return True

        except Exception as e:
            logger.error("Cache set error", key=cache_key, error=str(e))
            return False

    async def delete(self, prefix: str, key: str, **kwargs) -> bool:
        """Remove valor do cache."""
        if not self.is_connected:
            await self.connect()

        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            result = await self.redis_client.delete(cache_key)
            logger.debug("Cache delete", key=cache_key, deleted=bool(result))
            return bool(result)

        except Exception as e:
            logger.error("Cache delete error", key=cache_key, error=str(e))
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Remove múltiplas chaves por padrão."""
        if not self.is_connected:
            await self.connect()

        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info("Cache pattern delete", pattern=pattern, deleted=deleted)
                return deleted
            return 0

        except Exception as e:
            logger.error("Cache pattern delete error", pattern=pattern, error=str(e))
            return 0

    async def check_rate_limit(self, key: str, limit: int, window: int = 60) -> dict:
        """Check rate limit for a given key using sliding window."""
        if not self.is_connected:
            await self.connect()

        try:
            current_time = int(time.time())
            window_start = current_time - window

            # Use a sliding window approach with sorted sets
            pipe = self.redis_client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.zcard(key)
            pipe.expire(key, window)

            results = await pipe.execute()
            current_count = results[2]

            is_limited = current_count > limit
            remaining = max(0, limit - current_count)

            return {
                "allowed": not is_limited,
                "count": current_count,
                "remaining": remaining,
                "reset_time": current_time + window
            }

        except Exception as e:
            logger.error("Rate limit check error", key=key, error=str(e))
            # Fail open - allow the request if cache is down
            return {
                "allowed": True,
                "count": 0,
                "remaining": limit,
                "reset_time": int(time.time()) + window
            }

    async def increment(self, prefix: str, key: str, amount: int = 1, ttl: int = CacheConfig.DEFAULT_TTL, **kwargs) -> int:
        """Incrementa um contador no cache."""
        if not self.is_connected:
            await self.connect()

        cache_key = self._generate_key(prefix, key, **kwargs)

        try:
            # Usar pipeline para operação atômica
            pipe = self.redis_client.pipeline()
            pipe.incr(cache_key, amount)
            pipe.expire(cache_key, ttl)

            results = await pipe.execute()
            new_value = results[0]

            logger.debug("Cache increment", key=cache_key, amount=amount, new_value=new_value)
            return new_value

        except Exception as e:
            logger.error("Cache increment error", key=cache_key, error=str(e))
            return 0


# Instância global do cache
cache = RedisCache()


class CacheManager:
    """Gerenciador de cache com estratégias específicas para cada domínio."""

    def __init__(self, cache_instance: RedisCache):
        self.cache = cache_instance

    # === Cache de Usuários ===

    async def get_user(self, user_id: str) -> Optional[Dict]:
        """Cache de dados de usuário."""
        return await self.cache.get(CacheConfig.PREFIXES["user"], user_id)

    async def set_user(self, user_id: str, user_data: Dict) -> bool:
        """Cache de dados de usuário com TTL longo."""
        return await self.cache.set(
            CacheConfig.PREFIXES["user"],
            user_id,
            user_data,
            CacheConfig.LONG_TTL
        )

    async def invalidate_user(self, user_id: str) -> bool:
        """Invalida cache de usuário."""
        return await self.cache.delete(CacheConfig.PREFIXES["user"], user_id)

    # === Cache de Mídia ===

    async def get_media(self, media_id: str, include_relations: bool = False) -> Optional[Dict]:
        """Cache de dados de mídia."""
        return await self.cache.get(
            CacheConfig.PREFIXES["media"],
            media_id,
            relations=include_relations
        )

    async def set_media(self, media_id: str, media_data: Dict, include_relations: bool = False) -> bool:
        """Cache de dados de mídia."""
        return await self.cache.set(
            CacheConfig.PREFIXES["media"],
            media_id,
            media_data,
            CacheConfig.MEDIUM_TTL,
            relations=include_relations
        )

    async def invalidate_media(self, media_id: str) -> int:
        """Invalida todo cache relacionado a uma mídia."""
        pattern = f"{CacheConfig.PREFIXES['media']}{media_id}*"
        return await self.cache.delete_pattern(pattern)

    # === Rate Limiting ===

    async def check_rate_limit(self, identifier: str, limit: int, window: int = 60) -> dict:
        """Check rate limit using the underlying cache's rate limiting functionality."""
        return await self.cache.check_rate_limit(identifier, limit, window)


# Instância global do gerenciador
cache_manager = CacheManager(cache)
