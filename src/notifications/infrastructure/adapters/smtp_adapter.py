"""SMTP adapter (stub / no-op).

Este adapter não envia email de fato. Mantenha-o fora do catálogo público
até que um envio SMTP real seja implementado.
"""

from __future__ import annotations

import asyncio
from typing import Optional


class SMTPAdapter:
    """Stub que não envia email (placeholder controlado)."""

    def __init__(
        self,
        host: str = "",
        port: int = 0,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    async def send(self, recipient: Optional[str], subject: str, body: str) -> None:
        if not recipient:
            raise ValueError("Email do destinatário é obrigatório")
        # No-op: não envia
        await asyncio.sleep(0)


__all__ = ["SMTPAdapter"]
