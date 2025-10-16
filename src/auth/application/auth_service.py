# src/auth/application/auth_service.py - REFACTORED for SRP
from typing import Optional
from uuid import UUID

from src.auth.domain.user import User
from src.auth.application.services.authentication_service import AuthenticationService
from src.auth.application.services.user_registration_service import UserRegistrationService
from src.auth.application.services.user_administration_service import UserAdministrationService
from src.auth.application.services.password_service import PasswordService
from src.auth.application.queries.auth_queries import AuthQueries


class AuthService:
    """
    REFACTORED AuthService - Now follows Single Responsibility Principle.
    
    This service acts as a FACADE that coordinates specialized services.
    Each service has a single responsibility.
    
    Responsibilities:
    - Coordinate between specialized services
    - Provide unified interface for auth operations
    - Handle cross-cutting concerns (logging, metrics)
    """
    
    def __init__(
        self,
        authentication_service: AuthenticationService,
        registration_service: UserRegistrationService,
        administration_service: UserAdministrationService,
        password_service: PasswordService,
        auth_queries: AuthQueries,
    ):
        # Specialized services - each with single responsibility
        self.authentication_service = authentication_service
        self.registration_service = registration_service
        self.administration_service = administration_service
        self.password_service = password_service
        self.auth_queries = auth_queries

    # ===================================================================
    # USER REGISTRATION - Delegates to UserRegistrationService
    # ===================================================================
    
    async def create_user(self, email: str, password: str) -> User:
        """Create a new user. Delegates to specialized registration service."""
        return await self.registration_service.register_user(email, password)
    
    async def validate_registration_data(self, email: str, password: str) -> None:
        """Validate registration data. Delegates to registration service."""
        return await self.registration_service.validate_registration_data(email, password)

    # ===================================================================
    # AUTHENTICATION - Delegates to AuthenticationService  
    # ===================================================================

    async def authenticate_user(self, email: str, password: str) -> dict:
        """Authenticates a user and returns token info. Delegates to auth service."""
        return await self.authentication_service.authenticate(email, password)

    async def authenticate_user_and_get_token(self, email: str, password: str) -> dict:
        """Legacy method - same as authenticate_user."""
        return await self.authenticate_user(email, password)

    # ===================================================================
    # PASSWORD MANAGEMENT - Delegates to PasswordService
    # ===================================================================

    async def change_password(self, user_id: UUID, old_password: str, new_password: str) -> None:
        """Change user password. Delegates to specialized password service."""
        await self.password_service.change_password(user_id, old_password, new_password)
    
    async def validate_password_strength(self, password: str) -> None:
        """Validate password strength. Delegates to password service."""
        self.password_service.validate_password_strength(password)

    # ===================================================================
    # USER ADMINISTRATION - Delegates to UserAdministrationService
    # ===================================================================

    async def update_user(self, user_id: UUID, **kwargs) -> User:
        """Update user (admin operation). Delegates to administration service."""
        return await self.administration_service.update_user(user_id, **kwargs)

    async def delete_user(self, user_id: UUID) -> None:
        """Delete user (admin operation). Delegates to administration service."""
        await self.administration_service.delete_user(user_id)
    
    async def update_user_role(self, user_id: UUID, new_role: str) -> User:
        """Update user role (admin operation). Delegates to administration service."""
        return await self.administration_service.update_user_role(user_id, new_role)

    # ===================================================================
    # USER QUERIES - Delegates to AuthQueries
    # ===================================================================

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID. Delegates to query service."""
        try:
            return await self.auth_queries.find_by_id(UUID(user_id))
        except ValueError:
            return None
    
    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email. Delegates to query service."""
        return await self.auth_queries.find_by_email(email)
