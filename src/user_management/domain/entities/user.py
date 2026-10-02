from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.shared.domain.roles import UserRole  # perfil do núcleo compartilhado


@dataclass
class User:
    id: UUID
    email: str
    password_hash: str
    role: UserRole
    is_active: bool = True

    @classmethod
    def create(
        cls,
        email: str,
        password_hash: str,
        role: UserRole | str = UserRole.USER,
    ) -> "User":
        role_enum = role if isinstance(role, UserRole) else UserRole.normalize(str(role))
        return cls(id=uuid4(), email=email, password_hash=password_hash, role=role_enum)

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def change_email(self, email: str) -> None:
        from src.user_management.domain.rules import validate_email

        self.email = validate_email(email)

    def change_role(self, role: UserRole | str) -> None:
        from src.user_management.domain.rules import parse_role

        self.role = parse_role(role)

    def change_password_hash(self, password_hash: str) -> None:
        """O hash vem do adaptador de senhas; a regra de força é verificada antes."""
        self.password_hash = password_hash


__all__ = ["User", "UserRole"]
