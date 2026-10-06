from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.user_management.domain import User


class UserRepositoryPort(Protocol):
    async def save(self, user: User) -> User: ...
    async def delete(self, user_id: UUID) -> bool: ...
    async def find_by_id(self, user_id: UUID) -> User | None: ...
    async def find_by_email(self, email: str) -> User | None: ...
    async def list_all(self, *, page: int = 1, limit: int = 10, search: str | None = None): ...
    async def count_all(self) -> int: ...
    async def count_active(self) -> int: ...
    async def count_filtered(self, *, search: str | None = None): ...


class UserQueriesPort(Protocol):
    async def get_user_by_email(self, email: str) -> User | None: ...
    async def get_user_by_id(self, user_id: UUID) -> User | None: ...
    async def list_all(self, *, page: int = 1, limit: int = 10, search: str | None = None) -> list[User]: ...
    async def count_all(self) -> int: ...
    async def count_active(self) -> int: ...
    async def count_filtered(self, *, search: str | None = None) -> int: ...


class PasswordHasherPort(Protocol):
    def hash(self, password: str) -> str: ...
    def verify(self, password: str, hashed: str) -> bool: ...


class TokenProviderPort(Protocol):
    def create_access_token(self, user_id: UUID | str): ...
    def create_refresh_token(self, user_id: UUID | str): ...

    def create_scoped_token(
        self, user_id: UUID | str, purpose: str, ttl_seconds: int, resource: str | None = None
    ) -> str:
        """Token que só serve para ``purpose`` (e, se dado, para ``resource``)."""
        ...

    def verify_token(self, token: str) -> dict | None:
        """Conteúdo do token com assinatura e validade conferidas, ou None."""
        ...

    def verify_refresh_token(self, token: str) -> dict | None: ...


class RevokedTokensPort(Protocol):
    """Tokens de renovação invalidados antes do prazo (logout e rotação)."""

    async def revoke(self, token_id: str, ttl_seconds: int) -> None: ...

    async def is_revoked(self, token_id: str) -> bool: ...

    async def consume(self, token_id: str, ttl_seconds: int) -> bool:
        """Revoga e diz se esta chamada foi a primeira, numa operação só: duas
        renovações simultâneas com o mesmo token não podem passar as duas."""
        ...


class UserDataEraserPort(Protocol):
    """Apaga o que um módulo guarda de um usuário (mídias, avisos, avaliações).

    Cada módulo implementa a sua; este módulo só conhece a lista. Deve ser
    idempotente: uma exclusão interrompida pode ser repetida.
    """

    name: str

    async def erase(self, user_id: UUID) -> None: ...


class PermissionServicePort(Protocol):
    def require_admin(self, admin_user: User) -> None: ...
    def validate_admin_operation(self, admin_user: User, target_user_id: UUID) -> None: ...


class LoginAttemptLimiterPort(Protocol):
    """Contagem de tentativas de login malsucedidas por chave (e-mail, IP)."""

    async def retry_after(self, key: str) -> int:
        """Segundos até a chave ser liberada (0 = não bloqueada)."""
        ...

    async def register_failure(self, key: str, limit: int, window_seconds: int) -> None:
        """Registra uma falha; ao atingir ``limit`` na janela, bloqueia a chave."""
        ...

    async def reset(self, key: str) -> None: ...


__all__ = [
    "LoginAttemptLimiterPort",
    "UserRepositoryPort",
    "UserQueriesPort",
    "PasswordHasherPort",
    "TokenProviderPort",
    "PermissionServicePort",
    "UserDataEraserPort",
]
