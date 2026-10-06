"""Perfis de acesso: parte do núcleo compartilhado entre os contextos.

O perfil é definido pela gestão de usuários, mas as regras de acesso de
outros contextos (quem pode ver ou excluir uma mídia) dependem dele. Em vez
de cada contexto importar o domínio de usuários, o perfil fica aqui.
"""
from __future__ import annotations

from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"


__all__ = ["UserRole"]
