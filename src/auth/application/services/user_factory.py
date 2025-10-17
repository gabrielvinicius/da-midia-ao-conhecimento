# src/auth/application/services/user_factory.py
from src.auth.domain.user import User, UserRole
from src.shared.utils.id_generator import generate_id


class UserFactory:
    @staticmethod
    def create(email: str, hashed_password: str) -> User:
        """
        Creates a new User entity with default values.

        Args:
            email: The user's email address.
            hashed_password: The user's hashed password.

        Returns:
            A new User instance.
        """
        return User(
            id=generate_id(),
            email=email,
            password_hash=hashed_password,
            role=UserRole.USER,
        )
