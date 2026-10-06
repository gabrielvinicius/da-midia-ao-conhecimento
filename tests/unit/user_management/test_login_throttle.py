"""Proteção contra força bruta no login."""
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.shared.infrastructure.exceptions.exception_handlers import (
    register_exception_handlers,
)
from src.user_management.api import routers
from src.user_management.api.dependencies import (
    get_auth_service,
    get_auth_settings,
    get_login_throttle,
)
from src.user_management.application.services.login_throttle import LoginThrottle
from src.user_management.domain.errors import InvalidCredentialsError
from src.user_management.infrastructure.adapters.security.login_attempt_limiter import (
    InMemoryLoginAttemptLimiter,
    RedisLoginAttemptLimiter,
)


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


@pytest.mark.asyncio
async def test_memory_limiter_blocks_after_limit_and_unblocks_after_window():
    clock = Clock()
    limiter = InMemoryLoginAttemptLimiter(clock=clock)
    for _ in range(2):
        await limiter.register_failure("k", limit=3, window_seconds=60)
    assert await limiter.retry_after("k") == 0
    await limiter.register_failure("k", limit=3, window_seconds=60)
    assert 0 < await limiter.retry_after("k") <= 61
    clock.now += 61
    assert await limiter.retry_after("k") == 0


@pytest.mark.asyncio
async def test_memory_limiter_window_expires_failures():
    clock = Clock()
    limiter = InMemoryLoginAttemptLimiter(clock=clock)
    await limiter.register_failure("k", limit=2, window_seconds=60)
    clock.now += 120  # a falha antiga já saiu da janela
    await limiter.register_failure("k", limit=2, window_seconds=60)
    assert await limiter.retry_after("k") == 0


class FakeRedis:
    def __init__(self, broken=False):
        self.data, self.ttls, self.broken = {}, {}, broken

    def _check(self):
        if self.broken:
            raise ConnectionError("redis fora do ar")

    async def incr(self, key):
        self._check()
        self.data[key] = self.data.get(key, 0) + 1
        return self.data[key]

    async def expire(self, key, seconds):
        self._check()
        self.ttls[key] = seconds

    async def set(self, key, value, ex=None):
        self._check()
        self.data[key], self.ttls[key] = value, ex

    async def ttl(self, key):
        self._check()
        return self.ttls.get(key, -2) if key in self.data else -2

    async def delete(self, *keys):
        self._check()
        for key in keys:
            self.data.pop(key, None)
            self.ttls.pop(key, None)


@pytest.mark.asyncio
async def test_redis_limiter_blocks_and_resets():
    limiter = RedisLoginAttemptLimiter(FakeRedis())
    for _ in range(3):
        await limiter.register_failure("email:a@b.com", limit=3, window_seconds=900)
    assert await limiter.retry_after("email:a@b.com") == 900
    await limiter.reset("email:a@b.com")
    assert await limiter.retry_after("email:a@b.com") == 0


@pytest.mark.asyncio
async def test_redis_limiter_falls_back_to_memory_when_redis_is_down():
    limiter = RedisLoginAttemptLimiter(FakeRedis(broken=True))
    for _ in range(2):
        await limiter.register_failure("k", limit=2, window_seconds=900)
    assert await limiter.retry_after("k") > 0


@pytest.mark.asyncio
async def test_throttle_uses_email_and_ip_limits_and_success_resets_email():
    throttle = LoginThrottle(InMemoryLoginAttemptLimiter(), max_attempts_per_email=2, max_attempts_per_ip=3)
    await throttle.register_failure("A@b.com", "1.1.1.1")
    await throttle.register_success("a@b.com")  # e-mail normalizado
    await throttle.register_failure("a@b.com", "1.1.1.1")
    assert await throttle.retry_after("a@b.com", "9.9.9.9") == 0  # 1 falha desde o sucesso
    await throttle.register_failure("outro@b.com", "1.1.1.1")  # 3ª falha do mesmo IP
    assert await throttle.retry_after("novo@b.com", "1.1.1.1") > 0
    assert await throttle.retry_after("novo@b.com", "2.2.2.2") == 0


class FakeAuthService:
    async def authenticate_user(self, email, password):
        if password != "Certa123":
            raise InvalidCredentialsError("Credenciais inválidas")
        return {"access_token": "tok", "refresh_token": "ref"}


def test_login_route_returns_429_after_repeated_failures():
    app = FastAPI()
    register_exception_handlers(app)  # como na aplicação: credencial inválida vira 401
    app.include_router(routers.router)
    throttle = LoginThrottle(InMemoryLoginAttemptLimiter(), max_attempts_per_email=3, block_seconds=900)
    app.dependency_overrides[get_auth_service] = lambda: FakeAuthService()
    app.dependency_overrides[get_auth_settings] = lambda: SimpleNamespace(cookie_secure=False, cookie_samesite="lax")
    app.dependency_overrides[get_login_throttle] = lambda: throttle
    client = TestClient(app)

    wrong = {"username": "a@b.com", "password": "errada"}
    assert [client.post("/auth/token", data=wrong).status_code for _ in range(3)] == [401, 401, 401]

    blocked = client.post("/auth/token", data={"username": "a@b.com", "password": "Certa123"})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) > 0
