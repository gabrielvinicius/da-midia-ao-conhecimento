"""Simplified SMS adapter used for development and tests."""

from __future__ import annotations

import asyncio
from typing import Optional


class SmsAdapter:
    """Stub SMS adapter that simulates delivery by awaiting a noop."""

    async def send(self, phone_number: Optional[str], message: str) -> None:
        if not phone_number:
            raise ValueError("phone number is required to send SMS notifications")
        await asyncio.sleep(0)


__all__ = ["SmsAdapter"]
