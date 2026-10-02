"""Erros de negócio e de aplicação, com significado próprio.

Os serviços levantam estes erros; só a borda (rotas da API, tarefas da fila)
os traduz para HTTP ou para nova tentativa. Assim, nenhuma camada interna
precisa capturar Exception para decidir o que responder.
"""


class DomainError(Exception):
    """Regra de negócio violada (400)."""


class NotFoundError(DomainError, LookupError):
    """O recurso não existe, ou não pertence a quem pediu (404)."""


class ResourceNotFoundError(NotFoundError):
    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(f"{resource_type} with id {resource_id} not found")


class AccessDeniedError(DomainError, PermissionError):
    """Quem pediu não tem permissão para a operação (403)."""


class ConflictError(DomainError):
    """O estado atual do recurso não permite a operação (409)."""


class TemporarilyUnavailableError(DomainError):
    """Uma dependência falhou; nada ficou pela metade e a operação pode ser repetida (503)."""


class AuthenticationError(DomainError):
    """Credenciais ou sessão inválidas (401)."""


class ValidationError(DomainError):
    def __init__(self, field: str, value: str, message: str):
        super().__init__(f"Invalid value '{value}' for field '{field}': {message}")


__all__ = [
    "AccessDeniedError",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "ResourceNotFoundError",
    "TemporarilyUnavailableError",
    "ValidationError",
]
