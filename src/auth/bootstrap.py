# src/auth/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

# Infrastructure & Config
from src.auth.infrastructure.user_repository import UserRepository
from src.auth.config.settings import AuthSettings
from src.shared.monitoring.metrics_collector import MetricsCollector
from src.shared.domain.interfaces import CacheService
from src.auth.domain.interfaces import ITokenService, IUserSessionService, IUserSecurityService

# Queries
from src.auth.application.queries.auth_queries import AuthQueries

# Command Handlers
from src.auth.application.commands.handlers import (
    CreateUserCommandHandler,
    AuthenticateUserCommandHandler,
    ChangePasswordCommandHandler,
    UpdateUserCommandHandler,
    DeleteUserCommandHandler
)

# SRP Services (Factories, Validators, etc.)
from src.auth.application.services.user_validator import UserValidator
from src.auth.application.services.user_factory import UserFactory

# Specialized Services
from src.auth.application.services.password_service import PasswordService
from src.auth.application.services.user_registration_service import UserRegistrationService
from src.auth.application.services.authentication_service import AuthenticationService, EnhancedAuthenticationService
from src.auth.application.services.authentication_validator import AuthenticationValidator
from src.auth.application.services.authentication_metrics_service import AuthenticationMetricsService
from src.auth.application.services.user_administration_service import UserAdministrationService

def bootstrap_auth_module(
    db_session: AsyncSession,
    metrics_collector: MetricsCollector,
    cache_service: CacheService,
    token_service: ITokenService,
    session_service: IUserSessionService,
    security_service: IUserSecurityService
) -> Dict[str, Any]:
    """Constructs and returns the services for the auth module."""
    # --- Infrastructure and Config ---
    user_repository = UserRepository(db=db_session)
    auth_settings = AuthSettings()
    auth_queries = AuthQueries(user_repository=user_repository)

    # --- Command Handlers ---
    change_password_handler = ChangePasswordCommandHandler(user_repository=user_repository)
    authenticate_user_handler = AuthenticateUserCommandHandler(
        user_repository=user_repository, 
        settings=auth_settings
    )
    update_user_handler = UpdateUserCommandHandler(user_repository=user_repository)
    delete_user_handler = DeleteUserCommandHandler(user_repository=user_repository)

    # --- SRP Services for User Creation ---
    password_service = PasswordService(change_password_handler=change_password_handler)
    user_validator = UserValidator(user_repository=user_repository)
    user_factory = UserFactory()

    create_user_handler = CreateUserCommandHandler(
        user_repository=user_repository,
        user_validator=user_validator,
        password_service=password_service,
        user_factory=user_factory,
    )

    # --- SOLID Services (Following SRP) ---
    auth_validator = AuthenticationValidator()
    auth_metrics_service = AuthenticationMetricsService(
        metrics_collector=metrics_collector
    )
    
    # --- Enhanced Services ---
    registration_service = UserRegistrationService(create_user_handler=create_user_handler)
    
    # Legacy authentication service (for backward compatibility)
    authentication_service = AuthenticationService(
        authenticate_handler=authenticate_user_handler
    )
    
    # Enhanced authentication service (SOLID compliant)
    enhanced_authentication_service = EnhancedAuthenticationService(
        authenticate_handler=authenticate_user_handler,
        validator=auth_validator,
        metrics_service=auth_metrics_service,
        session_service=session_service,
        security_service=security_service,
        token_service=token_service
    )
    
    administration_service = UserAdministrationService(
        update_user_handler=update_user_handler,
        delete_user_handler=delete_user_handler,
        permission_service=None  # TODO: Implement permission service
    )

    return {
        # Infrastructure
        "user_repository": user_repository,
        "auth_queries": auth_queries,
        "auth_settings": auth_settings,
        
        # SOLID Services
        "auth_validator": auth_validator,
        "auth_metrics_service": auth_metrics_service,
        
        # Enhanced Services
        "enhanced_authentication_service": enhanced_authentication_service,
        "user_registration_service": registration_service,
        "user_administration_service": administration_service,
        "password_service": password_service,
        
        # Legacy compatibility
        "authentication_service": authentication_service,
    }
