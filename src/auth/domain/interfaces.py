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
    
    @abstractmethod
    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None:
        """Validate admin operation (raises exception if not allowed)."""
        pass


class IAuthenticationValidator(ABC):
    """Interface for authentication validation operations."""
    
    @abstractmethod
    def validate_login_credentials(self, email: str, password: str) -> None:
        """Validate login credentials format."""
        pass
    
    @abstractmethod
    def validate_token_format(self, token: str) -> None:
        """Validate token format."""
        pass
    
    @abstractmethod
    def validate_refresh_token(self, refresh_token: str) -> None:
        """Validate refresh token."""
        pass


class IAuthenticationMetricsService(ABC):
    """Interface for authentication metrics operations."""
    
    @abstractmethod
    def record_login_attempt(self, email: str, success: bool, ip_address: str) -> None:
        """Record login attempt for metrics."""
        pass
    
    @abstractmethod
    def record_token_generation(self, user_id: UUID, token_type: str) -> None:
        """Record token generation event."""
        pass
    
    @abstractmethod
    def record_authentication_failure(self, email: str, reason: str, ip_address: str) -> None:
        """Record authentication failure."""
        pass
    
    @abstractmethod
    def get_authentication_stats(self, time_range: str) -> dict:
        """Get authentication statistics."""
        pass


class IUserSessionService(ABC):
    """Interface for user session management."""
    
    @abstractmethod
    async def create_session(self, user_id: UUID, token: str, metadata: dict) -> str:
        """Create user session."""
        pass
    
    @abstractmethod
    async def validate_session(self, session_id: str) -> bool:
        """Validate user session."""
        pass
    
    @abstractmethod
    async def invalidate_session(self, session_id: str) -> None:
        """Invalidate user session."""
        pass
    
    @abstractmethod
    async def invalidate_all_user_sessions(self, user_id: UUID) -> int:
        """Invalidate all sessions for a user."""
        pass


class IUserSecurityService(ABC):
    """Interface for user security operations."""
    
    @abstractmethod
    async def check_account_security(self, user_id: UUID) -> dict:
        """Check account security status."""
        pass
    
    @abstractmethod
    async def detect_suspicious_activity(self, user_id: UUID, activity_data: dict) -> bool:
        """Detect suspicious user activity."""
        pass
    
    @abstractmethod
    async def enforce_rate_limiting(self, identifier: str, action: str) -> bool:
        """Enforce rate limiting for actions."""
        pass
    
    @abstractmethod
    async def log_security_event(self, user_id: UUID, event_type: str, details: dict) -> None:
        """Log security-related events."""
        pass


# Enhanced authentication service interface
class IEnhancedAuthenticationService(ABC):
    """Enhanced authentication service interface."""
    
    @abstractmethod
    async def authenticate_with_validation(
        self, 
        email: str, 
        password: str, 
        ip_address: str,
        user_agent: str
    ) -> dict:
        """Authenticate user with comprehensive validation."""
        pass
    
    @abstractmethod
    async def validate_and_refresh_token(self, refresh_token: str) -> dict:
        """Validate and refresh authentication token."""
        pass
    
    @abstractmethod
    async def logout_user(self, user_id: UUID, session_id: str) -> None:
        """Logout user and invalidate session."""
        pass
    
    @abstractmethod
    async def logout_all_sessions(self, user_id: UUID) -> int:
        """Logout user from all sessions."""
        pass