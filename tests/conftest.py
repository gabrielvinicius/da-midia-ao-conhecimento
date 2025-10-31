# tests/conftest.py
"""
Central pytest configuration for the entire test suite.
Provides shared fixtures, test utilities, and common setup for all test levels.
"""
import asyncio
import os
import sys
from pathlib import Path
import pytest
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# Ensure project modules are importable during tests
ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
for path in (ROOT_DIR, SRC_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# Import test utilities
from tests.mocks.in_memory_event_bus import InMemoryEventBus
from tests.mocks.in_memory_storage import InMemoryStorageService
from tests.utils.test_data_factory import TestDataFactory

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the entire test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """Configure test environment variables and settings."""
    os.environ["TESTING"] = "true"
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://test:test@localhost:5432/test_db"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["LOG_LEVEL"] = "DEBUG"
    yield
    # Cleanup environment after tests
    for key in ["TESTING", "DATABASE_URL", "REDIS_URL", "LOG_LEVEL"]:
        os.environ.pop(key, None)

# ============================================================================
# COMMON MOCKS AND FIXTURES
# ============================================================================

@pytest.fixture
def mock_event_bus() -> InMemoryEventBus:
    """Provides an in-memory event bus for testing event-driven functionality."""
    return InMemoryEventBus()

@pytest.fixture
def mock_storage_service() -> InMemoryStorageService:
    """Provides an in-memory storage service for testing file operations."""
    return InMemoryStorageService()

@pytest.fixture
def mock_connection_manager() -> AsyncMock:
    """Mock WebSocket connection manager for real-time communication testing."""
    manager = AsyncMock()
    manager.send_personal_message = AsyncMock()
    manager.send_broadcast_message = AsyncMock()
    manager.add_connection = AsyncMock()
    manager.remove_connection = AsyncMock()
    return manager

@pytest.fixture
def mock_metrics_service() -> MagicMock:
    """Mock metrics service for performance monitoring testing."""
    service = MagicMock()
    service.increment_counter = MagicMock()
    service.record_histogram = MagicMock()
    service.set_gauge = MagicMock()
    return service

@pytest.fixture
def test_data_factory() -> TestDataFactory:
    """Factory for creating test data objects with realistic values."""
    return TestDataFactory()

# ============================================================================
# DOMAIN-SPECIFIC MOCKS
# ============================================================================

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

@pytest.fixture
def mock_media_repository() -> AsyncMock:
    """Mock media repository for media management testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.find_by_id = AsyncMock()
    repo.find_by_user_id = AsyncMock()
    repo.update_status = AsyncMock()
    repo.delete = AsyncMock()
    return repo

@pytest.fixture
def mock_transcription_repository() -> AsyncMock:
    """Mock transcription repository for transcription module testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.find_by_id = AsyncMock()
    repo.find_by_media_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo

@pytest.fixture
def mock_summary_repository() -> AsyncMock:
    """Mock summary repository for summarization module testing."""
    repo = AsyncMock()
    repo.save = AsyncMock()
    repo.find_by_id = AsyncMock()
    repo.find_by_media_id = AsyncMock()
    repo.update = AsyncMock()
    repo.delete = AsyncMock()
    return repo

# ============================================================================
# EXTERNAL SERVICE MOCKS
# ============================================================================

@pytest.fixture
def mock_speech_recognition_service() -> AsyncMock:
    """Mock speech recognition service for transcription testing."""
    service = AsyncMock()
    service.transcribe = AsyncMock()
    service.get_supported_languages = AsyncMock(return_value=["en", "pt", "es"])
    service.validate_audio_format = AsyncMock(return_value=True)
    return service

@pytest.fixture
def mock_summarization_service() -> AsyncMock:
    """Mock summarization service for summary generation testing."""
    service = AsyncMock()
    service.summarize = AsyncMock()
    service.get_supported_strategies = AsyncMock(return_value=["extractive", "abstractive"])
    service.validate_text_length = AsyncMock(return_value=True)
    return service

@pytest.fixture
def mock_sentiment_analysis_service() -> AsyncMock:
    """Mock sentiment analysis service for emotion detection testing."""
    service = AsyncMock()
    service.analyze_sentiment = AsyncMock()
    service.analyze_emotions = AsyncMock()
    service.get_supported_models = AsyncMock(return_value=["bert", "distilbert"])
    return service

@pytest.fixture
def mock_topic_modeling_service() -> AsyncMock:
    """Mock topic modeling service for content analysis testing."""
    service = AsyncMock()
    service.extract_topics = AsyncMock()
    service.extract_keywords = AsyncMock()
    service.get_topic_coherence = AsyncMock()
    return service

# ============================================================================
# QUERY MOCKS
# ============================================================================

@pytest.fixture
def mock_media_queries() -> AsyncMock:
    """Mock media queries for CQRS pattern testing."""
    queries = AsyncMock()
    queries.get_by_id = AsyncMock()
    queries.get_by_user_id = AsyncMock()
    queries.get_with_status = AsyncMock()
    queries.search = AsyncMock()
    queries.get_statistics = AsyncMock()
    return queries

@pytest.fixture
def mock_auth_queries() -> AsyncMock:
    """Mock auth queries for user management testing."""
    queries = AsyncMock()
    queries.get_user_by_id = AsyncMock()
    queries.get_user_by_email = AsyncMock()
    queries.get_user_permissions = AsyncMock()
    queries.get_user_statistics = AsyncMock()
    return queries

@pytest.fixture
def mock_transcription_queries() -> AsyncMock:
    """Mock transcription queries for transcription analysis testing."""
    queries = AsyncMock()
    queries.get_by_id = AsyncMock()
    queries.get_by_media_id = AsyncMock()
    queries.get_with_speakers = AsyncMock()
    queries.search_by_content = AsyncMock()
    return queries

# ============================================================================
# INTEGRATION TEST UTILITIES
# ============================================================================

@pytest.fixture
def unique_test_id() -> str:
    """Generate a unique identifier for test isolation."""
    return str(uuid4())

@pytest.fixture
def test_user_data(unique_test_id: str) -> dict:
    """Generate test user data with unique email."""
    return {
        "email": f"test_user_{unique_test_id}@example.com",
        "password": "SecureTestPassword123!",
        "role": "USER"
    }

@pytest.fixture
def test_media_data(unique_test_id: str) -> dict:
    """Generate test media data for upload testing."""
    return {
        "filename": f"test_audio_{unique_test_id}.mp3",
        "content": b"fake_audio_content_for_testing",
        "content_type": "audio/mp3",
        "size": 1024
    }

# ============================================================================
# PERFORMANCE AND LOAD TESTING
# ============================================================================

@pytest.fixture
def performance_thresholds() -> dict:
    """Define performance thresholds for benchmark testing."""
    return {
        "api_response_time": 0.2,  # 200ms
        "db_query_time": 0.1,      # 100ms
        "file_upload_time": 2.0,   # 2s for 100MB
        "transcription_time": 10.0, # 10s for 1min audio
        "summarization_time": 5.0   # 5s for 1000 words
    }

@pytest.fixture
def load_test_config() -> dict:
    """Configuration for load testing scenarios."""
    return {
        "concurrent_users": 10,
        "requests_per_user": 5,
        "ramp_up_time": 30,
        "test_duration": 60
    }

# ============================================================================
# SECURITY TESTING
# ============================================================================

@pytest.fixture
def security_test_payloads() -> dict:
    """Malicious payloads for security testing."""
    return {
        "sql_injection": ["'; DROP TABLE users; --", "1' OR '1'='1"],
        "xss": ["<script>alert('xss')</script>", "javascript:alert('xss')"],
        "path_traversal": ["../../../etc/passwd", "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts"],
        "large_payload": "A" * 10000,
        "null_bytes": "\x00\x00\x00",
        "unicode_overflow": "ä" * 1000
    }

@pytest.fixture
def valid_jwt_token() -> str:
    """Generate a valid JWT token for authentication testing."""
    # This would normally use your JWT service
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test_token_for_testing"

# ============================================================================
# CLEANUP AND TEARDOWN
# ============================================================================

@pytest.fixture(autouse=True)
async def cleanup_test_artifacts():
    """Automatically cleanup test artifacts after each test."""
    yield
    # Cleanup logic here
    # - Clear temp files
    # - Reset mock states
    # - Clear caches
    pass

# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "slow: Slow running tests")

def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add markers based on test file paths
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Mark slow tests
        if item.get_closest_marker("slow") or "slow" in item.name:
            item.add_marker(pytest.mark.slow)