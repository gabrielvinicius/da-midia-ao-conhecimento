"""Envio de e-mails por SMTP (qualquer provedor: Resend, Brevo, Gmail, SES...)."""
from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid

from src.user_management.application.ports import EmailSenderPort


class SmtpEmailSender(EmailSenderPort):
    def __init__(self, host: str, port: int, username: str, password: str, sender: str, security: str = "starttls"):
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._from = sender
        self._security = (security or "starttls").lower()
        self.enabled = bool(host and sender)

    async def send(self, to: str, subject: str, body: str) -> None:
        if not self.enabled:
            return
        await asyncio.to_thread(self._send, to, subject, body)

    def _send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self._from
        message["To"] = to
        message["Subject"] = subject
        message["Message-ID"] = make_msgid(domain=self._from.rsplit("@", 1)[-1].strip("> ") or None)
        message.set_content(body)
        context = ssl.create_default_context()
        if self._security == "ssl":
            client = smtplib.SMTP_SSL(self._host, self._port, context=context, timeout=20)
        else:
            client = smtplib.SMTP(self._host, self._port, timeout=20)
        with client:
            if self._security == "starttls":
                client.starttls(context=context)
            if self._username:
                client.login(self._username, self._password)
            client.send_message(message)


class DisabledEmailSender(EmailSenderPort):
    """Sem servidor de e-mail configurado."""

    enabled = False

    async def send(self, to: str, subject: str, body: str) -> None:
        return None


def build_email_sender(settings) -> EmailSenderPort:
    if not settings.smtp_host or not settings.smtp_from:
        return DisabledEmailSender()
    return SmtpEmailSender(
        settings.smtp_host,
        settings.smtp_port,
        settings.smtp_username,
        settings.smtp_password,
        settings.smtp_from,
        settings.smtp_security,
    )


__all__ = ["DisabledEmailSender", "SmtpEmailSender", "build_email_sender"]
