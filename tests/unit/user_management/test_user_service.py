import pytest
from unittest.mock import AsyncMock, MagicMock
from src.user_management.application.user_service import UserService
from src.shared.infrastructure.settings import Settings

@pytest.fixture
def mock_settings():
    settings = Settings()
    # Override some settings if needed for tests, or use defaults
    # Since Settings loads from env, defaults are usually safe for unit tests 
    # as long as they don't hit external services.
    return settings

@pytest.fixture
def user_service(mock_user_repository, mock_settings):
    return UserService(user_repository=mock_user_repository, settings=mock_settings)

@pytest.mark.asyncio
async def test_create_user(user_service, mock_user_repository):
    mock_user_repository.find_by_email.return_value = None
    mock_user_repository.save.side_effect = lambda u: u
    
    user = await user_service.create_user("test@example.com", "Password123!")
    
    assert user.email == "test@example.com"
    mock_user_repository.save.assert_called_once()