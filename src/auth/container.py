# src/auth/container.py - REFACTORED for SRP
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.application.auth_service import AuthService
from src.auth.application.commands.create_user_command_handler import CreateUserCommandHandler
from src.auth.application.commands.authenticate_user_command_handler import AuthenticateUserCommandHandler
from src.auth.application.commands.update_user_command_handler import UpdateUserCommandHandler
from src.auth.application.commands.delete_user_command_handler import DeleteUserCommandHandler
from src.auth.application.commands.change_password_command_handler import ChangePasswordCommandHandler
from src.auth.application.queries.auth_queries import AuthQueries
from src.auth.config.settings import AuthSettings
from src.auth.infrastructure.user_repository import UserRepository

# Import refactored services
from src.auth.infrastructure.service_dependencies import (
    get_authentication_service,
    get_user_registration_service,
    get_user_administration_service,
    get_password_service,
    get_refactored_auth_service,
)


class AuthContainer:
    """
    REFACTORED Container for authentication module's dependencies.
    
    Now creates specialized services following Single Responsibility Principle.
    """
    def __init__(self, db_session: AsyncSession):
        self.settings = AuthSettings()
        self.user_repository = UserRepository(db=db_session)

        # Create Command Handlers
        create_user_handler = CreateUserCommandHandler(user_repository=self.user_repository)
        authenticate_user_handler = AuthenticateUserCommandHandler(
            user_repository=self.user_repository, 
            settings=self.settings
        )
        update_user_handler = UpdateUserCommandHandler(user_repository=self.user_repository)
        delete_user_handler = DeleteUserCommandHandler(user_repository=self.user_repository)
        change_password_handler = ChangePasswordCommandHandler(user_repository=self.user_repository)

        # Create Query Service
        self.queries = AuthQueries(user_repository=self.user_repository)

        # ===================================================================
        # Create Specialized Services (Single Responsibility each)
        # ===================================================================
        
        self.authentication_service = get_authentication_service(authenticate_user_handler)
        self.registration_service = get_user_registration_service(create_user_handler)
        self.administration_service = get_user_administration_service(update_user_handler, delete_user_handler)
        self.password_service = get_password_service(change_password_handler)

        # ===================================================================
        # Create Refactored Facade Service
        # ===================================================================
        
        self.service = get_refactored_auth_service(
            authentication_service=self.authentication_service,
            registration_service=self.registration_service,
            administration_service=self.administration_service,
            password_service=self.password_service,
            auth_queries=self.queries,
        )
