"""Erros do módulo de usuários, na hierarquia comum (traduzida para HTTP num só lugar)."""
from src.shared.domain.errors import AccessDeniedError, AuthenticationError, ConflictError, DomainError, NotFoundError


class UserAlreadyExistsError(ConflictError):
    def __init__(self, email: str = ""):
        super().__init__("Já existe uma conta com este e-mail.")
        self.email = email


class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: str = ""):
        super().__init__("Usuário não encontrado.")
        self.user_id = user_id


class InvalidCredentialsError(AuthenticationError):
    """Credenciais ou sessão inválidas (401)."""

    def __init__(self, message: str = "E-mail ou senha incorretos") -> None:
        super().__init__(message)


class InvalidUserDataError(DomainError):
    """Senha fraca, e-mail ou perfil inválidos, nada a atualizar (400)."""


class WrongCurrentPasswordError(DomainError):
    """Senha atual errada na troca de senha (400, não 401: a sessão continua válida)."""

    def __init__(self) -> None:
        super().__init__("Senha atual incorreta")


class EmailNotVerifiedError(AccessDeniedError):
    """Senha certa, mas o e-mail do cadastro ainda não foi confirmado (403).

    O 403 deixa a interface oferecer o reenvio do link; a senha já conferiu,
    então dizer isso não expõe nada."""

    def __init__(self) -> None:
        super().__init__("Confirme seu e-mail antes de entrar: use o link que enviamos ao criar a conta.")


class InvalidLinkError(DomainError):
    """Link de confirmação ou de nova senha inválido, expirado ou já usado (400)."""

    def __init__(self) -> None:
        super().__init__("Este link é inválido, expirou ou já foi usado. Peça um novo.")


__all__ = [
    "EmailNotVerifiedError",
    "InvalidLinkError",
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "InvalidCredentialsError",
    "InvalidUserDataError",
    "WrongCurrentPasswordError",
]
