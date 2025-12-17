from unittest.mock import AsyncMock

import pytest

from src.user_management.application.dtos import CreateUserCommand
from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.services.user_service import UserService
from src.user_management.config.settings import UserSettings
from src.user_management.domain.entities.user import UserRole


@pytest.fixture(autouse=True)
def patch_password_utils(monkeypatch):
    """Avoid bcrypt backend in unit scope."""
    from src.user_management.infrastructure.dependencies import providers
    monkeypatch.setattr(providers, "get_password_hasher", lambda: _FakeHasher())
    monkeypatch.setattr(providers, "get_token_provider", lambda: _FakeToken())


class _FakeHasher:
    def hash(self, password: str) -> str:
        return "hashed-password"

    def verify(self, password: str, hashed: str) -> bool:
        return True


class _FakeToken:
    def create_access_token(self, user_id):
        return "token"

    def verify_token(self, token: str):
        return {"sub": "user"}

@pytest.fixture
def mock_settings():
    settings = UserSettings()
    return settings

@pytest.fixture
def mock_user_read_service():
    service = AsyncMock(spec=UserReadService)
    # Default behavior: email not found
    service.get_user_by_email.return_value = None
    return service

@pytest.fixture
def user_service(mock_user_repository, mock_user_read_service, mock_settings):
    hasher = _FakeHasher()
    token = _FakeToken()
    return UserService(
        user_repository=mock_user_repository,
        user_read_service=mock_user_read_service,
        password_hasher=hasher,
        token_provider=token,
        settings=mock_settings
    )

@pytest.mark.asyncio
async def test_create_user(user_service, mock_user_repository, mock_user_read_service):
    # Setup
    mock_user_read_service.get_user_by_email.return_value = None
    mock_user_repository.save.side_effect = lambda u: u

    command = CreateUserCommand(email="test@example.com", password="Password123!", role=UserRole.USER)

    # Act
    user = await user_service.create_user(command)

    # Assert
    assert user.email == "test@example.com"
    mock_user_repository.save.assert_called_once()
    mock_user_read_service.get_user_by_email.assert_called_with("test@example.com")
