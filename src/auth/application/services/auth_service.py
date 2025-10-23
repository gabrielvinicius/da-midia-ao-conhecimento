# src/auth/application/services/auth_service.py
"""
Consolidated Auth Service - Handles all user and authentication operations.
This single service now contains the logic previously fragmented across
UserService, AuthService, PasswordService, and multiple command handlers.
"""
import structlog
from typing import Dict, Any, List, Optional
from uuid import UUID

from src.auth.domain.user import User, UserRole
from src.auth.infrastructure.user_repository import UserRepository
from src.auth.config.settings import AuthSettings
from src.shared.utils.id_generator import generate_id
from src.shared.utils.password_utils import hash_password, verify_password
from src.auth.utils.token import create_access_token

logger = structlog.get_logger(__name__)


class AuthService:
    """
    Consolidated service for all user and authentication operations.
    Handles: User CRUD, Authentication, Authorization, Password Management.
    """
    
    def __init__(
        self, 
        user_repository: UserRepository, 
        settings: AuthSettings
    ):
        self.user_repository = user_repository
        self.settings = settings

    # === Authentication ===

    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """Authenticate user and return token."""
        logger.info("auth.authenticate.started", email=email)
        user = await self.user_repository.find_by_email(email)
        if not user or not self._verify_password(password, user.password_hash):
            logger.warning("auth.authenticate.failed", email=email, reason="invalid_credentials")
            raise ValueError("Invalid credentials")
        
        token = create_access_token(user.id)
        logger.info("auth.authenticate.success", user_id=str(user.id))
        
        return {
            "token": token,
            "user": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role.value
            }
        }

    # === Core User Operations ===

    async def create_user(self, email: str, password: str, role: str = "user") -> User:
        """Create a new user with validation."""
        logger.info("user.create.started", email=email, role=role)
        self._validate_email_format(email)
        await self._validate_email_available(email)
        self._validate_password_strength(password)
        self._validate_role(role)

        password_hash = self._hash_password(password)

        new_user = User(
            id=generate_id(),
            email=email,
            password_hash=password_hash,
            role=UserRole(role),
        )
        
        created_user = await self.user_repository.save(new_user)
        logger.info("user.create.completed", user_id=str(created_user.id), email=email)
        return created_user

    async def update_user(self, user_id: UUID, updates: Dict[str, Any], admin_user_id: Optional[UUID] = None) -> User:
        """Update user information."""
        logger.info("user.update.started", user_id=str(user_id), updates=updates, admin_user_id=str(admin_user_id))
        user = await self._validate_user_exists(user_id)
        self._validate_user_updates(updates)

        for key, value in updates.items():
            setattr(user, key, value)

        updated_user = await self.user_repository.save(user)
        logger.info("user.update.completed", user_id=str(updated_user.id))
        return updated_user

    async def delete_user(self, user_id: UUID, admin_user_id: Optional[UUID] = None) -> bool:
        """Delete a user."""
        logger.info("user.delete.started", user_id=str(user_id), admin_user_id=str(admin_user_id))
        await self._validate_user_exists(user_id)
        success = await self.user_repository.delete(user_id)
        if success:
            logger.info("user.delete.completed", user_id=str(user_id))
        else:
            logger.error("user.delete.failed", user_id=str(user_id))
        return success

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> bool:
        """Change a user's password."""
        logger.info("user.change_password.started", user_id=str(user_id))
        user = await self._validate_user_exists(user_id)
        if not self._verify_password(old_password, user.password_hash):
            logger.warning("user.change_password.failed", reason="invalid_old_password", user_id=str(user_id))
            raise ValueError("Invalid old password")

        self._validate_password_strength(new_password)
        new_password_hash = self._hash_password(new_password)
        user.password_hash = new_password_hash
        await self.user_repository.save(user)
        
        logger.info("user.change_password.completed", user_id=str(user_id))
        return True

    # === Authorization & Permissions ===

    def require_admin_role(self, user: User) -> None:
        """Require user to have admin role."""
        if user.role != UserRole.ADMIN:
            raise PermissionError("Admin role required")

    def can_modify_user(self, current_user: User, target_user_id: UUID) -> bool:
        """Check if current user can modify target user."""
        if current_user.role == UserRole.ADMIN:
            return True
        return str(current_user.id) == str(target_user_id)

    # === Query Methods ===
    
    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        return await self.user_repository.find_by_id(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        return await self.user_repository.find_by_email(email)
    
    async def list_users(self) -> List[User]:
        return await self.user_repository.list_all()

    # === Private Helper & Validation Methods ===

    def _hash_password(self, password: str) -> str:
        return hash_password(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    async def _validate_user_exists(self, user_id: UUID) -> User:
        user = await self.user_repository.find_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        return user

    async def _validate_email_available(self, email: str) -> None:
        if await self.user_repository.find_by_email(email):
            raise ValueError("Email already registered")

    def _validate_email_format(self, email: str) -> None:
        if not email or '@' not in email or '.' not in email.split('@')[1]:
            raise ValueError("Invalid email format")

    def _validate_password_strength(self, password: str) -> None:
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one number")

    def _validate_role(self, role: str) -> None:
        valid_roles = [r.value for r in UserRole]
        if role not in valid_roles:
            raise ValueError(f"Invalid role. Must be one of: {valid_roles}")

    def _validate_user_updates(self, updates: Dict[str, Any]) -> None:
        if not updates:
            raise ValueError("No updates provided")
        if 'email' in updates:
            self._validate_email_format(updates['email'])
        if 'role' in updates:
            self._validate_role(updates['role'])
        
        forbidden_fields = ['id', 'password_hash', 'created_at']
        for field in forbidden_fields:
            if field in updates:
                raise ValueError(f"Cannot update field: {field}")
