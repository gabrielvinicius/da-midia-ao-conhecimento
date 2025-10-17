# tests/unit/auth/test_create_user_handler.py
"""
Unit tests for CreateUserCommandHandler.
Tests the CQRS command handling pattern for user creation with comprehensive scenarios.
"""
import pytest
from unittest.mock import AsyncMock
from datetime import datetime

from src.auth.application.commands.create_user_command import CreateUserCommand
from src.auth.application.commands.create_user_command_handler import CreateUserCommandHandler
from src.auth.domain.user import User, UserRole
from src.shared.exceptions.domain_exceptions import ValidationError, ResourceAlreadyExistsError


class TestCreateUserCommandHandler:
    """Test suite for CreateUserCommandHandler following DDD patterns."""

    @pytest.fixture
    def user_repository(self):
        """Mock user repository with all required methods."""
        repository = AsyncMock()
        repository.find_by_email = AsyncMock()
        repository.save = AsyncMock()
        repository.find_by_id = AsyncMock()
        return repository

    @pytest.fixture
    def user_validator(self):
        """Mock user validator."""
        validator = AsyncMock()
        validator.validate_new_user = AsyncMock()
        return validator

    @pytest.fixture
    def password_service(self):
        """Mock password service."""
        from unittest.mock import Mock
        service = Mock()
        service.hash_password = Mock(return_value="hashed_password_123")
        return service

    @pytest.fixture
    def user_factory(self):
        """Mock user factory."""
        from unittest.mock import Mock
        factory = Mock()
        factory.create = Mock()
        return factory

    @pytest.fixture
    def handler(self, user_repository, user_validator, password_service, user_factory):
        """CreateUserCommandHandler instance with mocked dependencies."""
        return CreateUserCommandHandler(
            user_repository=user_repository,
            user_validator=user_validator,
            password_service=password_service,
            user_factory=user_factory
        )

    @pytest.fixture
    def valid_command(self, test_data_factory):
        """Valid CreateUserCommand for testing."""
        user_data = test_data_factory.create_user_data()
        return CreateUserCommand(
            email=user_data["email"],
            password=user_data["password"]
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_success_with_default_role(self, handler, user_repository, user_validator, password_service, user_factory, valid_command, test_data_factory):
        """Test successful user creation with default USER role."""
        # Arrange
        expected_user = test_data_factory.create_user(
            email=valid_command.email,
            role=UserRole.USER
        )
        user_factory.create.return_value = expected_user
        user_repository.save.return_value = expected_user

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.email == valid_command.email
        assert result.role == UserRole.USER
        assert result.is_active is True
        
        # Verify all services were called correctly
        user_validator.validate_new_user.assert_awaited_once_with(valid_command.email)
        password_service.hash_password.assert_called_once_with(valid_command.password)
        user_factory.create.assert_called_once_with(valid_command.email, "hashed_password_123")
        user_repository.save.assert_awaited_once_with(expected_user)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_admin_user_success(self, handler, user_repository, test_data_factory):
        """Test successful admin user creation."""
        # Arrange
        admin_data = test_data_factory.create_user_data()
        command = CreateUserCommand(
            email=admin_data["email"],
            password=admin_data["password"]
        )
        user_repository.find_by_email.return_value = None
        expected_user = test_data_factory.create_admin_user(email=command.email)
        user_repository.save.return_value = expected_user

        # Act
        result = await handler.handle(command)

        # Assert
        assert result.email == command.email
        assert result.role == UserRole.ADMIN
        user_repository.find_by_email.assert_awaited_once_with(command.email)
        user_repository.save.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_email_already_exists(self, handler, user_repository, valid_command, test_data_factory):
        """Test that ResourceAlreadyExistsError is raised when email already exists."""
        # Arrange
        existing_user = test_data_factory.create_user(email=valid_command.email)
        user_repository.find_by_email.return_value = existing_user

        # Act & Assert
        with pytest.raises(ResourceAlreadyExistsError, match="Email already registered"):
            await handler.handle(valid_command)
        
        user_repository.find_by_email.assert_awaited_once_with(valid_command.email)
        user_repository.save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_invalid_email_format(self, handler, user_repository):
        """Test that ValidationError is raised for invalid email format."""
        # Arrange
        invalid_command = CreateUserCommand(
            email="invalid_email_format",
            password="ValidPassword123!"
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid email format"):
            await handler.handle(invalid_command)
        
        user_repository.find_by_email.assert_not_awaited()
        user_repository.save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_weak_password(self, handler, user_repository, test_data_factory):
        """Test that ValidationError is raised for weak password."""
        # Arrange
        user_data = test_data_factory.create_user_data()
        weak_password_command = CreateUserCommand(
            email=user_data["email"],
            password="123"  # Too weak
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Password does not meet security requirements"):
            await handler.handle(weak_password_command)
        
        user_repository.find_by_email.assert_not_awaited()
        user_repository.save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_invalid_role(self, handler, user_repository, test_data_factory):
        """Test that ValidationError is raised for invalid role."""
        # Arrange
        user_data = test_data_factory.create_user_data()
        invalid_role_command = CreateUserCommand(
            email=user_data["email"],
            password=user_data["password"]
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Invalid user role"):
            await handler.handle(invalid_role_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_repository_error(self, handler, user_repository, valid_command):
        """Test error handling when repository operation fails."""
        # Arrange
        user_repository.find_by_email.return_value = None
        user_repository.save.side_effect = Exception("Database connection error")

        # Act & Assert
        with pytest.raises(Exception, match="Database connection error"):
            await handler.handle(valid_command)
        
        user_repository.find_by_email.assert_awaited_once()
        user_repository.save.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_password_hashing_security(self, handler, user_repository, valid_command):
        """Test that password is properly hashed using BCrypt."""
        # Arrange
        user_repository.find_by_email.return_value = None
        created_user = User(
            id="test_id",
            email=valid_command.email,
            password_hash="$2b$12$hashed_password_example",
            role=UserRole.USER
        )
        user_repository.save.return_value = created_user

        # Act
        result = await handler.handle(valid_command)

        # Assert
        saved_user = user_repository.save.await_args.args[0]
        # BCrypt hash characteristics
        assert saved_user.password_hash.startswith("$2b$")
        assert len(saved_user.password_hash) >= 60
        assert saved_user.password_hash != valid_command.password

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_sets_default_timestamps(self, handler, user_repository, valid_command):
        """Test that user creation sets appropriate timestamps."""
        # Arrange
        user_repository.find_by_email.return_value = None
        user_repository.save.return_value = User(
            id="test_id",
            email=valid_command.email,
            password_hash="hashed",
            role=UserRole.USER,
            created_at=datetime.utcnow()
        )

        # Act
        await handler.handle(valid_command)

        # Assert
        saved_user = user_repository.save.await_args.args[0]
        assert saved_user.created_at is not None
        assert isinstance(saved_user.created_at, datetime)
        assert saved_user.is_active is True

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_email_case_insensitive(self, handler, user_repository, test_data_factory):
        """Test that email comparison is case-insensitive."""
        # Arrange
        user_data = test_data_factory.create_user_data()
        existing_user = test_data_factory.create_user(email=user_data["email"].upper())
        user_repository.find_by_email.return_value = existing_user
        
        command = CreateUserCommand(
            email=user_data["email"].lower(),
            password=user_data["password"]
        )

        # Act & Assert
        with pytest.raises(ResourceAlreadyExistsError, match="Email already registered"):
            await handler.handle(command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_user_email_normalization(self, handler, user_repository, valid_command):
        """Test that email is normalized before storage."""
        # Arrange
        user_repository.find_by_email.return_value = None
        user_repository.save.return_value = User(
            id="test_id",
            email=valid_command.email.lower().strip(),
            password_hash="hashed",
            role=UserRole.USER
        )

        # Act
        await handler.handle(valid_command)

        # Assert
        saved_user = user_repository.save.await_args.args[0]
        assert saved_user.email == valid_command.email.lower().strip()
        assert "@" in saved_user.email
        assert " " not in saved_user.email
