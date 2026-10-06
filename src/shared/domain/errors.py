"""Erros de negócio e de aplicação, com significado próprio.

Os serviços levantam estes erros; só a borda (rotas da API, tarefas da fila)
os traduz para HTTP ou para nova tentativa. Assim, nenhuma camada interna
precisa capturar Exception para decidir o que responder.
"""


class DomainError(Exception):
    """Regra de negócio violada (400)."""


class NotFoundError(DomainError, LookupError):
    """O recurso não existe, ou não pertence a quem pediu (404)."""


class AccessDeniedError(DomainError, PermissionError):
    """Quem pediu não tem permissão para a operação (403)."""


class ConflictError(DomainError):
    """O estado atual do recurso não permite a operação (409)."""


class TemporarilyUnavailableError(DomainError):
    """Uma dependência falhou; nada ficou pela metade e a operação pode ser repetida (503)."""


class AuthenticationError(DomainError):
    """Credenciais ou sessão inválidas (401)."""


class ValidationError(DomainError):
    """Valor inválido num campo (400). A mensagem chega ao usuário."""

    def __init__(self, field: str, value: str, message: str):
        super().__init__(f"Valor inválido para {field} ({value!r}): {message}.")
        self.field = field


def is_permanent_failure(exc: BaseException) -> bool:
    """Outra tentativa daria o mesmo resultado: regra violada, recurso
    ausente, arquivo inválido. A exceção é a dependência fora do ar
    (TemporarilyUnavailableError), que pode voltar. Erros fora da hierarquia
    (falta de memória na GPU, falha de leitura) também podem passar."""
    return isinstance(exc, DomainError) and not isinstance(exc, TemporarilyUnavailableError)


__all__ = [
    "AccessDeniedError",
    "ConflictError",
    "DomainError",
    "NotFoundError",
    "TemporarilyUnavailableError",
    "ValidationError",
    "is_permanent_failure",
]
