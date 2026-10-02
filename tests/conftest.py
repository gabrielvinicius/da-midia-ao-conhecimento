import asyncio
import os
import tempfile
import warnings
from typing import Generator
from unittest.mock import AsyncMock

import pytest

# Import test utilities
from tests.mocks.in_memory_event_bus import InMemoryEventBus
from tests.mocks.in_memory_storage import InMemoryStorage
from tests.utils.test_data_factory import TestDataFactory

# For coleções/lightweight defaults, habilita bootstrap leve antes da coleta
def pytest_configure(config):
    os.environ.setdefault("LIGHTWEIGHT_BOOTSTRAP", "1")
    try:
        from src.shared.infrastructure.observability.logging.logging_config import configure_logging
        configure_logging("test", level="DEBUG", log_format="console")
    except ImportError:
        pass

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

# Evitar warning do joblib em ambientes com /dev/shm restrito.
_joblib_tmp = os.path.join(tempfile.gettempdir(), "joblib")
os.makedirs(_joblib_tmp, exist_ok=True)
os.environ.setdefault("JOBLIB_TEMP_FOLDER", _joblib_tmp)
warnings.filterwarnings("ignore", message=".*joblib will operate in serial mode.*", category=UserWarning, module="joblib.*")
# Silenciar DeprecationWarning do passlib que importa crypt (Python 3.12+)
warnings.filterwarnings("ignore", message=".*'crypt' is deprecated.*", category=DeprecationWarning, module="passlib.utils")

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the entire test session."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Factory for creating test data objects with realistic values."""
    return TestDataFactory()

@pytest.fixture
def mock_event_bus() -> InMemoryEventBus:
    """Provides an in-memory event bus for testing event-driven functionality."""
    return InMemoryEventBus()

@pytest.fixture
def mock_storage_service() -> InMemoryStorage:
    """Provides an in-memory storage service for testing file operations."""
    return InMemoryStorage()


@pytest.fixture
def fake_metrics():
    """Generic fake metrics port that records calls."""
    class _FakeMetrics:
        def __init__(self):
            self.calls = []

        async def record_operation(self, **kwargs):
            self.calls.append(kwargs)
            return None

        def set_context(self, *args, **kwargs):
            return None
    return _FakeMetrics()


@pytest.fixture
def fake_cache():
    """Simple in-memory cache fake with dict semantics."""
    store = {}
    class _Cache:
        async def get(self, key, default=None):
            return store.get(key, default)
        async def set(self, key, value, expire=None):
            store[key] = value
        async def delete(self, key):
            store.pop(key, None)
    return _Cache()

@pytest.fixture
def mock_user_repository() -> AsyncMock:
    """Mock user repository for auth module testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.find_by_id = AsyncMock()
    repo.find_by_email = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo
