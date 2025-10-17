# src/auth/application/commands/create_user_command_handler.py
from src.auth.domain.user import User
from src.auth.infrastructure.user_repository import UserRepository
from ..services.user_validator import UserValidator
from ..services.password_service import PasswordService
from ..services.user_factory import UserFactory
from .create_user_command import CreateUserCommand


class CreateUserCommandHandler:
    def __init__(
        self,
        user_repository: UserRepository,
        user_validator: UserValidator,
        password_service: PasswordService,
        user_factory: UserFactory,
    ):
        self.user_repository = user_repository
        self.user_validator = user_validator
        self.password_service = password_service
        self.user_factory = user_factory

    async def handle(self, command: CreateUserCommand) -> User:
        """Orchestrates the user creation workflow."""
        # 1. Validate
        await self.user_validator.validate_new_user(command.email)

        # 2. Hash Password
        hashed_password = self.password_service.hash_password(command.password)

        # 3. Create Entity
        user = self.user_factory.create(command.email, hashed_password)

        # 4. Persist
        return await self.user_repository.save(user)
