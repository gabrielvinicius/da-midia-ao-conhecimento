class UserAlreadyExistsError(Exception):
    """Usuário já existe."""


class UserNotFoundError(Exception):
    """Usuário não encontrado."""


class InvalidCredentialsError(Exception):
    """Credenciais inválidas."""


__all__ = [
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "InvalidCredentialsError",
]
