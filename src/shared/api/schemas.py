"""Esquemas comuns das rotas."""
from typing import Generic, List, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int

    @staticmethod
    def pages_for(total: int, limit: int) -> int:
        return -(-total // limit) if limit else 1


__all__ = ["PaginatedResponse"]
