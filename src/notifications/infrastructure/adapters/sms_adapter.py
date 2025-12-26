"""SMS adapter (stub / no-op).

Não realiza envio real de SMS; mantenha fora do catálogo público até haver
integração com um provider de fato.
"""

from __future__ import annotations

import asyncio
from typing import Optional


class SmsAdapter:
    """Stub SMS adapter that simulates delivery by awaiting a noop."""

    async def send(self, phone_number: Optional[str], message: str) -> None:
        if not phone_number:
            raise ValueError("Número de telefone é obrigatório para enviar SMS")
        await asyncio.sleep(0)


__all__ = ["SmsAdapter"]
