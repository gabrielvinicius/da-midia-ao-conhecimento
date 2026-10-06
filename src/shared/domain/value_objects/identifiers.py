"""Identificadores compartilhados entre os módulos.

Nos eventos e nas tarefas, os identificadores viajam como texto (o formato
da fila). Ao entrar num módulo, viram UUID por parse_id, em um só lugar, em
vez de cada handler converter e tratar o erro do seu jeito.
"""
from __future__ import annotations

from typing import NewType, Optional
from uuid import UUID

from src.shared.domain.errors import ValidationError

MediaId = NewType("MediaId", UUID)
UserId = NewType("UserId", UUID)


def parse_id(value: object) -> Optional[UUID]:
    """UUID do valor; None se vazio. Texto inválido é erro de validação."""
    if value is None or value == "":
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except ValueError:
        raise ValidationError("id", str(value), "identificador inválido") from None


def parse_media_id(value: object) -> MediaId:
    media_id = parse_id(value)
    if media_id is None:
        raise ValidationError("media_id", "", "identificador da mídia ausente")
    return MediaId(media_id)


__all__ = ["MediaId", "UserId", "parse_id", "parse_media_id"]
