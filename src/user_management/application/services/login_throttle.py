"""Regra de limitação de tentativas de login (proteção contra força bruta)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.user_management.application.ports import LoginAttemptLimiterPort


@dataclass
class LoginThrottle:
    """Bloqueia temporariamente e-mails e IPs com muitas falhas de login.

    O limite por e-mail protege cada conta; o limite por IP, mais alto, dificulta
    testar muitas contas a partir da mesma origem. Um login bem-sucedido zera o
    contador do e-mail (não o do IP).
    """

    limiter: LoginAttemptLimiterPort
    max_attempts_per_email: int = 5
    max_attempts_per_ip: int = 20
    block_seconds: int = 15 * 60

    @staticmethod
    def _email_key(email: str) -> str:
        return f"email:{email.strip().lower()}"

    @staticmethod
    def _ip_key(ip: Optional[str]) -> Optional[str]:
        return f"ip:{ip}" if ip else None

    async def retry_after(self, email: str, ip: Optional[str]) -> int:
        waits = [await self.limiter.retry_after(self._email_key(email))]
        ip_key = self._ip_key(ip)
        if ip_key:
            waits.append(await self.limiter.retry_after(ip_key))
        return max(waits)

    async def register_failure(self, email: str, ip: Optional[str]) -> None:
        await self.limiter.register_failure(
            self._email_key(email), self.max_attempts_per_email, self.block_seconds
        )
        ip_key = self._ip_key(ip)
        if ip_key:
            await self.limiter.register_failure(ip_key, self.max_attempts_per_ip, self.block_seconds)

    async def register_success(self, email: str) -> None:
        await self.limiter.reset(self._email_key(email))
