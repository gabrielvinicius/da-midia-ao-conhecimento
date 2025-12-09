"""Simplified webhook adapter for local usage."""

from __future__ import annotations

import asyncio
from typing import Any, Dict


class WebhookAdapter:
    """Stub webhook adapter that records a payload asynchronously."""

    async def send(self, payload: str, metadata: Dict[str, Any] | None = None) -> None:
        await asyncio.sleep(0)


__all__ = ["WebhookAdapter"]
