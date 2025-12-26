"""Webhook adapter (stub / no-op).

Não entrega webhooks reais; use apenas para desenvolvimento/teste.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict


class WebhookAdapter:
    """Stub webhook adapter that simulates asynchronous delivery."""

    async def send(self, payload: str, metadata: Dict[str, Any] | None = None) -> None:
        await asyncio.sleep(0)


__all__ = ["WebhookAdapter"]
