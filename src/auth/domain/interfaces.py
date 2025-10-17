"""
Domain interfaces for authentication module.
Follows Dependency Inversion Principle (DIP).
"""
from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from src.auth.domain.user import User


class IUserRepository(ABC):
    """Interface for user repository operations."""
    
    @abstractmethod
    async def save(self, user: User) -> User:
        """Save or update a user."""
        pass
    
    @abstractmethod
    async def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Find user by ID."""
        pass
    
    @abstractmethod
    async def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        pass
    
    @abstractmethod
    async def list_all(self, page: int = 1, limit: int = 10, search: Optional[str] = None) -> List[User]:
        """List users with pagination and search."""
        pass
    
    @abstractmethod
    async def delete(self, user_id: UUID) -> bool:
        """Delete a user."""
        pass


class IPasswordService(ABC):
    """Interface for password operations."""
    
    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash a password."""
        pass
    
    @abstractmethod
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        pass


class ITokenService(ABC):
    """Interface for JWT token operations."""
    
    @abstractmethod
    def create_access_token(self, data: dict) -> str:
        """Create an access token."""
        pass
    
    @abstractmethod
    def create_refresh_token(self, data: dict) -> str:
        """Create a refresh token."""
        pass
    
    @abstractmethod
    def verify_token(self, token: str) -> dict:
        """Verify and decode a token."""
        pass
    
    @abstractmethod
    def refresh_access_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token."""
        pass


class IUserValidator(ABC):
    """Interface for user validation operations."""
    
    @abstractmethod
    async def validate_email_uniqueness(self, email: str, exclude_user_id: Optional[UUID] = None) -> None:
        """Validate that email is unique."""
        pass
    
    @abstractmethod
    def validate_password_strength(self, password: str) -> None:
        """Validate password meets requirements."""
        pass
    
    @abstractmethod
    def validate_email_format(self, email: str) -> None:
        """Validate email format."""
        pass


class IUserPermissionService(ABC):
    """Interface for user permission validation."""
    
    @abstractmethod
    def can_perform_admin_operation(self, admin_user: User, target_user_id: UUID) -> bool:
        """Check if user can perform admin operation."""
        pass
    
    @abstractmethod
    def can_access_resource(self, user: User, resource_id: UUID, operation: str) -> bool:
        """Check if user can access specific resource."""
        pass