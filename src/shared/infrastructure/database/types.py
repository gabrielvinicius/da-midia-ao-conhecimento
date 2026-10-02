"""Tipos de coluna compartilhados pelos modelos."""
from __future__ import annotations

from enum import Enum
from typing import Type

from sqlalchemy import Enum as SqlEnum

ENUM_LENGTH = 32


def enum_column(enum_class: Type[Enum]) -> SqlEnum:
    """Enum gravado como texto (o nome do membro), validado pela aplicação.

    Os enums nativos do PostgreSQL exigiam migração para incluir ou remover um
    valor (vimos isso nos tipos de aviso); como texto, basta mudar o enum.
    """
    return SqlEnum(enum_class, native_enum=False, length=ENUM_LENGTH, validate_strings=True)


__all__ = ["ENUM_LENGTH", "enum_column"]
