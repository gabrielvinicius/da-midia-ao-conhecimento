"""Simplified SMTP adapter for local testing."""

from __future__ import annotations

import asyncio
from typing import Optional


class SMTPAdapter:
    """Coarse SMTP adapter that pretends to send emails."""

    def __init__(
        self,
        host: str,
        port: int,
        username: Optional[str],
        password: Optional[str],
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password

    async def send(self, recipient: Optional[str], subject: str, body: str) -> None:
        if not recipient:
            raise ValueError("recipient email is required")
        await asyncio.sleep(0)


__all__ = ["SMTPAdapter"]
