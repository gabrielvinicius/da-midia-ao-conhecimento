"""
Consolidated User Service - Handles all user-related operations
Consolidates: UserValidator, UserFactory, UserRegistrationService, UserAdministrationService
"""
import structlog
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.auth.domain.user import User, UserRole
# FIXED: Application should not import Infrastructure directly
from src.shared.application.dependency_injection import get_user_repository
from src.auth.application.commands.commands import (
    CreateUserCommand,
    UpdateUserCommand,
    DeleteUserCommand
)
from src.auth.application.commands.handlers import (
    CreateUserCommandHandler,
    UpdateUserCommandHandler,
    DeleteUserCommandHandler
)
from src.shared.utils.id_generator import generate_id
from src.shared.utils.password_utils import hash_password

logger = structlog.get_logger(__name__)


class UserService:
    """
    Consolidated service for all user operations.
    Handles: CRUD, validation, creation, administration.
    """
    
    def __init__(
        self,
        user_repository: UserRepository,
        create_user_handler: CreateUserCommandHandler,
        update_user_handler: UpdateUserCommandHandler,
        delete_user_handler: DeleteUserCommandHandler
    ):
        self.user_repository = user_repository
        self.create_user_handler = create_user_handler
        self.update_user_handler = update_user_handler
        self.delete_user_handler = delete_user_handler

    # === USER CREATION & REGISTRATION ===
    
    async def create_user(self, email: str, password: str, role: str = "user") -> Dict[str, Any]:
        """Create a new user with validation."""
        # Validate email availability
        await self._validate_email_available(email)
        
        # Validate email format
        self._validate_email_format(email)
        
        # Create and execute command
        command = CreateUserCommand(email=email, password=password, role=role)
        return await self.create_user_handler.handle(command)
    
    async def register_user(self, email: str, password: str) -> Dict[str, Any]:
        """Register a new user (public registration)."""
        return await self.create_user(email, password, role="user")

    # === USER ADMINISTRATION ===
    
    async def update_user(self, user_id: UUID, updates: Dict[str, Any], admin_user_id: Optional[UUID] = None) -> Dict[str, Any]:
        """Update user information."""
        # Validate user exists
        await self._validate_user_exists(user_id)
        
        # Validate updates
        self._validate_user_updates(updates)
        
        command = UpdateUserCommand(
            user_id=user_id,
            updates=updates,
            admin_user_id=admin_user_id
        )
        return await self.update_user_handler.handle(command)
    
    async def delete_user(self, user_id: UUID, admin_user_id: UUID) -> Dict[str, Any]:
        """Delete a user (admin operation)."""
        # Validate user exists
        await self._validate_user_exists(user_id)
        
        command = DeleteUserCommand(user_id=user_id, admin_user_id=admin_user_id)
        return await self.delete_user_handler.handle(command)
    
    async def change_user_role(self, user_id: UUID, new_role: str, admin_user_id: UUID) -> Dict[str, Any]:
        """Change user role."""
        # Validate role
        self._validate_role(new_role)
        
        return await self.update_user(
            user_id=user_id,
            updates={"role": new_role},
            admin_user_id=admin_user_id
        )

    # === USER FACTORY METHODS ===
    
    def create_user_entity(self, email: str, hashed_password: str, role: str = "user") -> User:
        """Create a new User entity."""
        return User(
            id=generate_id(),
            email=email,
            password_hash=hashed_password,
            role=UserRole(role),
        )

    # === VALIDATION METHODS ===
    
    async def _validate_email_available(self, email: str) -> None:
        """Validate email is not already registered."""
        if await self.user_repository.find_by_email(email):
            raise ValueError("Email already registered")
    
    async def _validate_user_exists(self, user_id: UUID) -> User:
        """Validate user exists and return it."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        return user
    
    def _validate_email_format(self, email: str) -> None:
        """Validate email format."""
        if not email or '@' not in email or '.' not in email.split('@')[1]:
            raise ValueError("Invalid email format")
    
    def _validate_role(self, role: str) -> None:
        """Validate role is valid."""
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")
    
    def _validate_user_updates(self, updates: Dict[str, Any]) -> None:
        """Validate user update data."""
        if not updates:
            raise ValueError("No updates provided")
        
        # Validate email if being updated
        if 'email' in updates:
            self._validate_email_format(updates['email'])
        
        # Validate role if being updated
        if 'role' in updates:
            self._validate_role(updates['role'])
        
        # Prevent updating sensitive fields directly
        forbidden_fields = ['id', 'password_hash', 'created_at']
        for field in forbidden_fields:
            if field in updates:
                raise ValueError(f"Cannot update field: {field}")

    # === QUERY METHODS ===
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return await self.user_repository.get_by_id(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return await self.user_repository.find_by_email(email)
    
    async def list_users(self) -> List[User]:
        """List all users (admin operation)."""
        return await self.user_repository.list_all()
    
    async def count_users(self) -> int:
        """Count total users."""
        return await self.user_repository.count()
    
    async def check_email_availability(self, email: str) -> bool:
        """Check if email is available for registration."""
        try:
            await self._validate_email_available(email)
            return True
        except ValueError:
            return False