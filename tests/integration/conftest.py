import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app
from src.media_management.api.dependencies import get_media_service
from src.media_management.application.services.media_read_service import MediaReadService
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.config.settings import media_settings
from src.media_management.infrastructure.adapters.storage_uploader_adapter import (
    DefaultUploadMetadataMapper,
)
from src.user_management.api.dependencies import get_auth_service, get_user_service, get_auth_queries, get_auth_settings, get_login_throttle
from src.user_management.application.services.login_throttle import LoginThrottle
from src.user_management.infrastructure.adapters.security.login_attempt_limiter import InMemoryLoginAttemptLimiter
from tests.mocks.fake_auth import build_fake_auth, seed_default_user
from tests.mocks.fake_media_repository import FakeMediaRepository
from tests.mocks.fake_storage_uploader import FakeStorageUploadAdapter, FakeStorageUploader
from tests.mocks.in_memory_event_bus import InMemoryEventBus
from tests.mocks.in_memory_storage import InMemoryStorage


@pytest_asyncio.fixture
async def client():
    """HTTPX client bound to the FastAPI app for integration tests, com fakes in-memory."""
    async with app.router.lifespan_context(app):
        # Override dependências após o bootstrap real para manter fakes
        # Serviços reais de autenticação sobre um repositório em memória:
        # as rotas de login e cadastro não têm mais atalhos de teste.
        auth_service, user_service, auth_queries, user_repo = build_fake_auth()

        app.dependency_overrides[get_auth_queries] = lambda: auth_queries
        app.dependency_overrides[get_auth_settings] = lambda: user_service.settings
        app.dependency_overrides[get_user_service] = lambda: user_service
        app.dependency_overrides[get_auth_service] = lambda: auth_service
        # Limitador de login isolado por teste (sem estado compartilhado)
        login_throttle = LoginThrottle(InMemoryLoginAttemptLimiter())
        app.dependency_overrides[get_login_throttle] = lambda: login_throttle

        storage = InMemoryStorage()
        storage_uploader = FakeStorageUploader(FakeStorageUploadAdapter(storage))
        metadata_mapper = DefaultUploadMetadataMapper()
        media_repo = FakeMediaRepository()
        media_read_service = MediaReadService(media_repo)
        fake_event_bus = InMemoryEventBus()
        media_service = MediaService(
            media_repository=media_repo,
            storage_uploader=storage_uploader,
            metadata_mapper=metadata_mapper,
            metrics_service=fake_event_bus,  # no-op metrics
            upload_validator=MediaUploadValidator(media_settings),
            media_read_service=media_read_service,
            event_bus=fake_event_bus,
            storage_maintenance=None,
                                    storage_downloader=None,
        )
        app.dependency_overrides[get_media_service] = lambda: media_service

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            # Seed default user and auth header
            user = await seed_default_user(user_service, "test@example.com", "Password123")
            token = auth_service.user_service.token_provider.create_access_token(user.id)
            c.headers["Authorization"] = f"Bearer {token}"
            yield c


@pytest_asyncio.fixture
async def authenticated_user(client):
    """Mantido para compatibilidade; já há Authorization header no client."""
    return None


@pytest.fixture(autouse=True)
def enable_lightweight_mode(monkeypatch) -> None:
    """Use lightweight bootstrap during integration tests to avoid real infra."""
    monkeypatch.setenv("LIGHTWEIGHT_BOOTSTRAP", "1")
    monkeypatch.setenv("CELERY_BROKER_URL", "memory://")
    monkeypatch.setenv("CELERY_RESULT_BACKEND", "cache+memory://")
    monkeypatch.setenv("CELERY_TASK_ALWAYS_EAGER", "1")
    monkeypatch.setenv("CELERY_TASK_EAGER_PROPAGATES", "1")
