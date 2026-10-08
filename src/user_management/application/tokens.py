"""Finalidades dos tokens emitidos pela autenticação.

O token de acesso vai no cabeçalho Authorization. Onde o navegador não deixa
mandar cabeçalho (a URL do vídeo no <video>, a abertura do WebSocket), vai um
token de finalidade restrita: só serve para aquilo, por pouco tempo. Antes,
o próprio token de acesso ia na URL (e nos logs do proxy) e expirava em 30
minutos, no meio de uma aula longa.
"""
from __future__ import annotations

from enum import Enum


class TokenPurpose(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"
    MEDIA_STREAM = "media_stream"  # reprodução de uma mídia
    NOTIFICATIONS = "notifications"  # abertura do WebSocket de avisos
    # Links enviados por e-mail (não são emitidos pela rota /scoped-token).
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


SCOPED_PURPOSES = frozenset({TokenPurpose.MEDIA_STREAM, TokenPurpose.NOTIFICATIONS})

__all__ = ["SCOPED_PURPOSES", "TokenPurpose"]
