from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from src.shared.domain.roles import UserRole  # perfil do núcleo compartilhado
from src.user_management.domain.rules import parse_role, validate_email


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
        """E-mail e perfil passam pelas mesmas regras da alteração: antes, um
        perfil inválido virava USER sem aviso aqui e era recusado na alteração."""
        return cls(id=uuid4(), email=validate_email(email), password_hash=password_hash, role=parse_role(role))

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False

    def change_email(self, email: str) -> None:
        self.email = validate_email(email)

    def change_role(self, role: UserRole | str) -> None:
        self.role = parse_role(role)

    def change_password_hash(self, password_hash: str) -> None:
        """O hash vem do adaptador de senhas; a regra de força é verificada antes."""
        self.password_hash = password_hash


__all__ = ["User", "UserRole"]
