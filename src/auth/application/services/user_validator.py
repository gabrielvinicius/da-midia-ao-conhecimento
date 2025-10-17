# src/auth/application/services/user_validator.py
from src.auth.infrastructure.user_repository import UserRepository


class UserValidator:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def validate_new_user(self, email: str) -> None:
        """
        Validates that a new user can be created.

        Args:
            email: The email to validate.

        Raises:
            ValueError: If the email is already registered.
        """
        if await self.user_repository.find_by_email(email):
            raise ValueError("Email already registered")
