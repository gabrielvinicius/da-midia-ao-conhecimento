"""Unidade de trabalho: várias gravações confirmadas juntas, ou nenhuma."""
from __future__ import annotations

from typing import AsyncContextManager, Protocol


class UnitOfWorkPort(Protocol):
    def transaction(self) -> AsyncContextManager[None]:
        """Tudo o que os repositórios gravarem dentro do bloco é confirmado ao
        fim, de uma vez; uma exceção desfaz tudo."""
        ...


__all__ = ["UnitOfWorkPort"]
