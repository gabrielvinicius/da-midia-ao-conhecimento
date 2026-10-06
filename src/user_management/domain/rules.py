"""Regras da conta: e-mail, senha e perfil.

Ficavam no serviço, que alterava os campos do usuário diretamente; agora a
entidade só muda por estes métodos e regras.
"""
from __future__ import annotations

from src.shared.domain.roles import UserRole
from src.user_management.domain.errors import InvalidUserDataError


def normalize_email(email: str) -> str:
    """E-mails comparados sem diferença de maiúsculas: ``A@x.com`` e ``a@x.com``
    eram duas contas, e o login dependia de como o endereço foi digitado."""
    return (email or "").strip().lower()


def validate_email(email: str) -> str:
    email = normalize_email(email)
    if "@" not in email or "." not in email.split("@")[-1]:
        raise InvalidUserDataError("Formato de email inválido")
    return email


def validate_password(password: str, min_length: int) -> None:
    if len(password) < min_length:
        raise InvalidUserDataError(f"Senha deve ter pelo menos {min_length} caracteres")
    if not any(c.isupper() for c in password):
        raise InvalidUserDataError("Senha deve conter ao menos uma letra maiúscula")
    if not any(c.islower() for c in password):
        raise InvalidUserDataError("Senha deve conter ao menos uma letra minúscula")
    if not any(c.isdigit() for c in password):
        raise InvalidUserDataError("Senha deve conter ao menos um número")


def parse_role(role: UserRole | str) -> UserRole:
    if isinstance(role, UserRole):
        return role
    try:
        return UserRole(str(getattr(role, "value", role)).upper())
    except ValueError:
        valid = ", ".join(r.value for r in UserRole)
        raise InvalidUserDataError(f"Perfil inválido. Perfis válidos: {valid}") from None


__all__ = ["normalize_email", "validate_email", "validate_password", "parse_role"]
