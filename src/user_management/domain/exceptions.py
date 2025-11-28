"""Domain exceptions for User Management."""

class UserManagementError(Exception):
    """Base exception for user management domain."""
    pass

class UserAlreadyExistsError(UserManagementError):
    """Raised when attempting to create a user that already exists."""
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"User with email {email} already exists.")

class UserNotFoundError(UserManagementError):
    """Raised when a requested user is not found."""
    def __init__(self, identifier: str):
        super().__init__(f"User not found: {identifier}")

class InvalidCredentialsError(UserManagementError):
    """Raised when authentication fails."""
    def __init__(self):
        super().__init__("Invalid email or password.")
