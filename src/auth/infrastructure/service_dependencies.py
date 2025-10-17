"""
Auth Service Dependencies - Dependency Injection for Refactored Services
"""
from src.auth.application.services.authentication_service import AuthenticationService
from src.auth.application.services.user_registration_service import UserRegistrationService
from src.auth.application.services.user_administration_service import UserAdministrationService
from src.auth.application.services.password_service import PasswordService
from src.auth.application.auth_service import AuthService

# Import command handlers
from src.auth.application.commands.authenticate_user_command_handler import AuthenticateUserCommandHandler
from src.auth.application.commands.create_user_command_handler import CreateUserCommandHandler
from src.auth.application.commands.update_user_command_handler import UpdateUserCommandHandler
from src.auth.application.commands.delete_user_command_handler import DeleteUserCommandHandler
from src.auth.application.commands.change_password_command_handler import ChangePasswordCommandHandler

# Import queries
from src.auth.application.queries.auth_queries import AuthQueries

# Import repository
from src.auth.infrastructure.user_repository import UserRepository


def get_authentication_service(
    authenticate_handler: AuthenticateUserCommandHandler,
) -> AuthenticationService:
    """Create AuthenticationService with dependencies."""
    return AuthenticationService(authenticate_handler)


def get_user_registration_service(
    create_user_handler: CreateUserCommandHandler,
) -> UserRegistrationService:
    """Create UserRegistrationService with dependencies."""
    return UserRegistrationService(create_user_handler)


def get_user_administration_service(
    update_user_handler: UpdateUserCommandHandler,
    delete_user_handler: DeleteUserCommandHandler,
) -> UserAdministrationService:
    """Create UserAdministrationService with dependencies."""
    return UserAdministrationService(update_user_handler, delete_user_handler)


def get_password_service(
    change_password_handler: ChangePasswordCommandHandler,
) -> PasswordService:
    """Create PasswordService with dependencies."""
    return PasswordService(change_password_handler)


def get_refactored_auth_service(
    authentication_service: AuthenticationService,
    registration_service: UserRegistrationService,
    administration_service: UserAdministrationService,
    password_service: PasswordService,
    auth_queries: AuthQueries,
) -> AuthService:
    """
    Create refactored AuthService with specialized services.
    
    This replaces the old AuthService constructor that had too many dependencies.
    Now each service has a single responsibility.
    """
    return AuthService(
        authentication_service=authentication_service,
        registration_service=registration_service,
        administration_service=administration_service,
        password_service=password_service,
        auth_queries=auth_queries,
    )


# Legacy support - for gradual migration
def get_legacy_auth_service(
    create_user_handler: CreateUserCommandHandler,
    authenticate_user_handler: AuthenticateUserCommandHandler,
    update_user_handler: UpdateUserCommandHandler,
    delete_user_handler: DeleteUserCommandHandler,
    change_password_handler: ChangePasswordCommandHandler,
    auth_queries: AuthQueries,
) -> AuthService:
    """
    Create AuthService using the new refactored approach.
    
    This function helps migrate from the old constructor to the new one.
    It creates the specialized services internally.
    """
    # Create specialized services
    authentication_service = get_authentication_service(authenticate_user_handler)
    registration_service = get_user_registration_service(create_user_handler)
    administration_service = get_user_administration_service(update_user_handler, delete_user_handler)
    password_service = get_password_service(change_password_handler)
    
    # Create refactored AuthService
    return get_refactored_auth_service(
        authentication_service=authentication_service,
        registration_service=registration_service,
        administration_service=administration_service,
        password_service=password_service,
        auth_queries=auth_queries,
    )