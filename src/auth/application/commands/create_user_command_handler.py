# src/auth/application/commands/create_user_command_handler.py
from src.auth.domain.user import User, UserRole
from src.auth.infrastructure.user_repository import UserRepository
from src.shared.utils.id_generator import generate_id
from src.shared.utils.password_utils import hash_password
from .create_user_command import CreateUserCommand


class CreateUserCommandHandler:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def handle(self, command: CreateUserCommand) -> User:
        """Handles the user creation process."""
        if await self.user_repository.find_by_email(command.email):
            raise ValueError("Email already registered")

        hashed_password = hash_password(command.password)
        user = User(
            id=generate_id(),
            email=command.email,
            password_hash=hashed_password,
            role=UserRole.USER
        )
        return await self.user_repository.save(user)
