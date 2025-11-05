"""Runtime settings for notification adapters.

These lightweight defaults allow the notification pipeline to be imported in
test environments where real SMTP credentials are unavailable. The values can
be overridden via environment variables when running the full stack.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(slots=True)
class SmtpSettings:
    """Minimal configuration object consumed by notification tasks."""

    smtp_host: str = os.getenv("SMTP_HOST", "localhost")
    smtp_port: int = int(os.getenv("SMTP_PORT", "1025"))
    smtp_user: str | None = os.getenv("SMTP_USER")
    smtp_password: str | None = os.getenv("SMTP_PASSWORD")


__all__ = ["SmtpSettings"]
