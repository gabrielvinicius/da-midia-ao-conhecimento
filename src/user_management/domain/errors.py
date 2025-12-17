class UserAlreadyExistsError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


__all__ = [
    "UserAlreadyExistsError",
    "UserNotFoundError",
    "InvalidCredentialsError",
]
