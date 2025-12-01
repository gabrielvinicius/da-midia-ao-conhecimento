import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Import test utilities
from tests.mocks.in_memory_event_bus import InMemoryEventBus
from tests.mocks.in_memory_storage import InMemoryStorageService
from tests.utils.test_data_factory import TestDataFactory

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

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
def mock_storage_service() -> InMemoryStorageService:
    """Provides an in-memory storage service for testing file operations."""
    return InMemoryStorageService()

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