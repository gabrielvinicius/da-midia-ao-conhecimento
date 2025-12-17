class DomainError(Exception):
    """Base class for domain errors."""


class ResourceNotFoundError(DomainError):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} with id {resource_id} not found")


class ValidationError(DomainError):
    def __init__(self, field: str, value: str, message: str):
        super().__init__(f"Invalid value '{value}' for field '{field}': {message}")


__all__ = [
    "DomainError",
    "ResourceNotFoundError",
    "ValidationError",
]
