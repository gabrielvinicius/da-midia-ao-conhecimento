# src/auth/bootstrap.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

# Infrastructure & Config
from src.auth.infrastructure.user_repository import UserRepository
from src.auth.config.settings import AuthSettings

# Queries
from src.auth.application.queries.auth_queries import AuthQueries

# Command Handlers
from src.auth.application.commands.create_user_command_handler import CreateUserCommandHandler
from src.auth.application.commands.authenticate_user_command_handler import AuthenticateUserCommandHandler
from src.auth.application.commands.change_password_command_handler import ChangePasswordCommandHandler
from src.auth.application.commands.update_user_command_handler import UpdateUserCommandHandler
from src.auth.application.commands.delete_user_command_handler import DeleteUserCommandHandler

# SRP Services (Factories, Validators, etc.)
from src.auth.application.services.user_validator import UserValidator
from src.auth.application.services.user_factory import UserFactory

# Specialized Services (for Facade)
from src.auth.application.services.password_service import PasswordService
from src.auth.application.services.user_registration_service import UserRegistrationService
from src.auth.application.services.authentication_service import AuthenticationService
from src.auth.application.services.user_administration_service import UserAdministrationService

# Main Facade Service
from src.auth.application.auth_service import AuthService


def bootstrap_auth_module(db_session: AsyncSession) -> Dict[str, Any]:
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

    # Refactored CreateUserCommandHandler with its new dependencies
    create_user_handler = CreateUserCommandHandler(
        user_repository=user_repository,
        user_validator=user_validator,
        password_service=password_service,
        user_factory=user_factory,
    )

    # --- Specialized Services for Facade ---
    registration_service = UserRegistrationService(create_user_handler=create_user_handler)
    authentication_service = AuthenticationService(
        authenticate_user_handler=authenticate_user_handler,
        password_service=password_service
    )
    administration_service = UserAdministrationService(
        update_user_handler=update_user_handler,
        delete_user_handler=delete_user_handler,
        user_repository=user_repository
    )

    # --- Main Facade Service ---
    auth_service = AuthService(
        authentication_service=authentication_service,
        registration_service=registration_service,
        administration_service=administration_service,
        password_service=password_service,
        auth_queries=auth_queries,
    )

    return {
        "user_repository": user_repository,
        "auth_service": auth_service,
        "auth_queries": auth_queries,
        "auth_settings": auth_settings,
    }
