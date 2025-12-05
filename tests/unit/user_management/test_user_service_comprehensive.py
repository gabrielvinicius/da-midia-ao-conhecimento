"""Comprehensive unit tests for UserService."""
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from pytest import fixture

from src.user_management.application.user_service import UserService
from src.user_management.domain.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from src.user_management.domain.user import User, UserRole
from src.user_management.infrastructure.user_repository import UserRepository
from src.shared.utils.password_utils import hash_password

@fixture
def mock_user_repository():
    return MagicMock(spec=UserRepository)

@fixture
def user_service(mock_user_repository):
    return UserService(user_repository=mock_user_repository)

@fixture
def sample_user():
    return User(
        id=uuid.uuid4(),
        email="test@example.com",
        password_hash=hash_password("OldPassword123!"),
        role=UserRole.USER,
        is_active=True
    )

@pytest.mark.asyncio
class TestUserService:
    
    # --- Create User ---

    async def test_create_user_success(self, user_service, mock_user_repository):
        email = "new@example.com"
        password = "StrongPassword123!"
        
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_user_repository.save = AsyncMock(side_effect=lambda u: u)
        
        user = await user_service.create_user(email, password)
        
        assert user.email == email
        assert user.role == UserRole.USER
        mock_user_repository.save.assert_called_once()

    async def test_create_user_duplicate_email(self, user_service, mock_user_repository, sample_user):
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        
        with pytest.raises(UserAlreadyExistsError):
            await user_service.create_user(sample_user.email, "Password123!")

    async def test_create_user_weak_password(self, user_service, mock_user_repository):
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        
        with pytest.raises(ValueError, match="at least 8 characters"):
            await user_service.create_user("valid@email.com", "weak")

    async def test_create_user_invalid_email(self, user_service):
        with pytest.raises(ValueError, match="Invalid email"):
            await user_service.create_user("not-an-email", "Password123!")

    # --- Authenticate User ---

    async def test_authenticate_success(self, user_service, mock_user_repository, sample_user):
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        
        result = await user_service.authenticate_user(sample_user.email, "OldPassword123!")
        
        assert "token" in result
        assert result["user"]["email"] == sample_user.email

    async def test_authenticate_user_not_found(self, user_service, mock_user_repository):
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        
        with pytest.raises(InvalidCredentialsError):
            await user_service.authenticate_user("unknown@example.com", "Password123!")

    async def test_authenticate_wrong_password(self, user_service, mock_user_repository, sample_user):
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        
        with pytest.raises(InvalidCredentialsError):
            await user_service.authenticate_user(sample_user.email, "WrongPassword123!")

    # --- Update User ---

    async def test_update_user_email_success(self, user_service, mock_user_repository, sample_user):
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_user_repository.save = AsyncMock(side_effect=lambda u: u)
        
        updated_user = await user_service.update_user(sample_user.id, {"email": "updated@example.com"})
        
        assert updated_user.email == "updated@example.com"
        mock_user_repository.save.assert_called_once()

    async def test_update_user_email_duplicate(self, user_service, mock_user_repository, sample_user):
        existing_user = User(id=uuid.uuid4(), email="taken@example.com", password_hash="...", role=UserRole.USER)
        
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_user_repository.find_by_email = AsyncMock(return_value=existing_user)
        
        with pytest.raises(UserAlreadyExistsError):
            await user_service.update_user(sample_user.id, {"email": "taken@example.com"})

    async def test_update_user_restricted_fields(self, user_service, mock_user_repository, sample_user):
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        
        with pytest.raises(ValueError, match="Cannot update fields"):
            await user_service.update_user(sample_user.id, {"password_hash": "hacked"})

    # --- Change Password ---

    async def test_change_password_success(self, user_service, mock_user_repository, sample_user):
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_user_repository.save = AsyncMock(side_effect=lambda u: u)
        
        old_hash = sample_user.password_hash
        await user_service.change_password(sample_user.id, "OldPassword123!", "NewStrongPassword123!")
        
        assert mock_user_repository.save.called
        # Verify that save was called with a user having a different hash
        saved_user = mock_user_repository.save.call_args[0][0]
        assert saved_user.password_hash != old_hash

    async def test_change_password_wrong_old(self, user_service, mock_user_repository, sample_user):
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        
        with pytest.raises(InvalidCredentialsError):
            await user_service.change_password(sample_user.id, "WrongOld123!", "NewStrongPassword123!")
