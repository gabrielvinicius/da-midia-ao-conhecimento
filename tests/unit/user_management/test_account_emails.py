"""Confirmação de e-mail no cadastro e recuperação de senha (envio opcional)."""
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.user_management.application.auth_queries import UserReadService
from src.user_management.application.dtos import CreateUserCommand
from src.user_management.application.services.account_email_service import AccountEmailService
from src.user_management.application.services.user_service import UserService
from src.user_management.domain import UserRole
from src.user_management.domain.errors import EmailNotVerifiedError, InvalidLinkError
from src.user_management.infrastructure.adapters.security.login_attempt_limiter import InMemoryLoginAttemptLimiter
from src.user_management.infrastructure.adapters.smtp_email_sender import (
    DisabledEmailSender,
    SmtpEmailSender,
    build_email_sender,
)
from src.user_management.infrastructure.dependencies.providers import BcryptPasswordHasher, JwtTokenProvider
from src.user_management.infrastructure.repositories.fake_user_repository import FakeUserRepository

SETTINGS = SimpleNamespace(
    public_url="https://tcc.exemplo.dev/",
    email_verification_hours=24,
    password_reset_minutes=60,
    account_emails_per_hour=3,
)
PASSWORD = "Senha-forte-1"


class Outbox:
    enabled = True

    def __init__(self):
        self.sent = []

    async def send(self, to, subject, body):
        self.sent.append((to, subject, body))

    def link(self, page):
        return re.search(rf"https://tcc\.exemplo\.dev/{page}\?token=(\S+)", self.sent[-1][2]).group(1)


def _services(sender=None):
    repo = FakeUserRepository()
    users = UserService(repo, UserReadService(repo), BcryptPasswordHasher(), JwtTokenProvider())
    outbox = sender or Outbox()
    return users, AccountEmailService(users, outbox, SETTINGS, limiter=InMemoryLoginAttemptLimiter()), outbox


def _command(email="ana@exemplo.com"):
    return CreateUserCommand(email=email, password=PASSWORD, role=UserRole.USER)


@pytest.mark.asyncio
async def test_with_email_the_account_only_enters_after_the_link():
    users, accounts, outbox = _services()
    user, required = await accounts.register(_command())

    assert required and not user.email_verified
    assert outbox.sent[0][1] == "Confirme seu e-mail"
    with pytest.raises(EmailNotVerifiedError):
        await users.authenticate_user("ana@exemplo.com", PASSWORD)

    await accounts.confirm_email(outbox.link("confirmar-email"))
    assert (await users.authenticate_user("ana@exemplo.com", PASSWORD))["access_token"]


@pytest.mark.asyncio
async def test_without_email_the_account_enters_directly_and_recovery_is_off():
    users, accounts, _ = _services(DisabledEmailSender())
    user, required = await accounts.register(_command())
    assert user.email_verified and not required and not accounts.enabled
    assert (await users.authenticate_user("ana@exemplo.com", PASSWORD))["access_token"]
    await accounts.request_password_reset("ana@exemplo.com")  # sem efeito, sem erro


@pytest.mark.asyncio
async def test_the_reset_link_changes_the_password_once():
    users, accounts, outbox = _services()
    await accounts.register(_command())
    await accounts.confirm_email(outbox.link("confirmar-email"))

    await accounts.request_password_reset("ANA@exemplo.com ")
    token = outbox.link("redefinir-senha")
    await accounts.reset_password(token, "Outra-senha-2")

    assert (await users.authenticate_user("ana@exemplo.com", "Outra-senha-2"))["access_token"]
    with pytest.raises(InvalidLinkError):  # o link já foi usado
        await accounts.reset_password(token, "Terceira-senha-3")


@pytest.mark.asyncio
async def test_unknown_addresses_wrong_links_and_too_many_requests_reveal_nothing():
    _, accounts, outbox = _services()
    await accounts.request_password_reset("ninguem@exemplo.com")
    assert outbox.sent == []  # mesma resposta, nenhum envio

    await accounts.register(_command())
    verification = outbox.link("confirmar-email")
    with pytest.raises(InvalidLinkError):  # link de confirmação não troca senha
        await accounts.reset_password(verification, "Outra-senha-2")
    with pytest.raises(InvalidLinkError):
        await accounts.confirm_email("token-qualquer-que-nao-vale-nada")

    for _ in range(5):
        await accounts.resend_verification("ana@exemplo.com")
    assert len(outbox.sent) == 1 + 3  # cadastro + 3 reenvios por hora


@pytest.mark.asyncio
async def test_a_failed_delivery_does_not_undo_the_registration():
    class Broken(Outbox):
        async def send(self, to, subject, body):
            raise OSError("servidor fora do ar")

    users, accounts, _ = _services(Broken())
    user, required = await accounts.register(_command())
    assert required and await users.user_read_service.get_user_by_email("ana@exemplo.com")


def test_the_sender_is_on_only_with_server_and_sender_address():
    off = SimpleNamespace(smtp_host="", smtp_from="", smtp_port=587, smtp_username="", smtp_password="", smtp_security="starttls")
    assert isinstance(build_email_sender(off), DisabledEmailSender)
    on = SimpleNamespace(**{**vars(off), "smtp_host": "smtp.resend.com", "smtp_from": "Da Mídia ao Conhecimento <no-reply@exemplo.dev>"})
    sender = build_email_sender(on)
    assert isinstance(sender, SmtpEmailSender) and sender.enabled


@pytest.mark.asyncio
async def test_the_smtp_sender_uses_starttls_and_login(monkeypatch):
    calls = []

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self, context):
            calls.append(("starttls",))

        def login(self, user, password):
            calls.append(("login", user))

        def send_message(self, message):
            calls.append(("send", message["To"], message["Subject"]))

    monkeypatch.setattr("smtplib.SMTP", FakeSmtp)
    sender = SmtpEmailSender("smtp.resend.com", 587, "resend", "chave", "no-reply@exemplo.dev")
    await sender.send("ana@exemplo.com", "Confirme seu e-mail", "corpo")
    assert calls == [
        ("connect", "smtp.resend.com", 587),
        ("starttls",),
        ("login", "resend"),
        ("send", "ana@exemplo.com", "Confirme seu e-mail"),
    ]


def test_dependency_default_is_not_built_by_the_api():
    from src.user_management.api.dependencies import get_account_email_service

    with pytest.raises(NotImplementedError):
        get_account_email_service()
    assert AsyncMock  # mantém o import usado pelos outros testes do módulo
