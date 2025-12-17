"""Provider registry for notifications bounded context."""
from __future__ import annotations

from typing import Callable, Dict

from src.notifications.application.ports import (
    ConnectionManagerPort,
    EmailSenderPort,
    PushSenderPort,
    SMSSenderPort,
)
from src.notifications.config.settings import notification_settings
from src.notifications.infrastructure.adapters.sms_adapter import SMSAdapter
from src.notifications.infrastructure.adapters.smtp_adapter import SMTPAdapter
from src.notifications.infrastructure.adapters.webhook_adapter import WebhookAdapter
from src.notifications.infrastructure.adapters.websockets.connection_manager import (
    manager as websocket_connection_manager,
)
from src.user_management.application.auth_queries import UserReadService
from src.user_management.infrastructure.dependencies.auth_queries_adapter import (
    AuthQueriesAdapter,
)
from src.user_management.infrastructure.repositories.sqlalchemy_user_repository import (
    UserRepository,
)

_EMAIL_SENDERS: Dict[str, Callable[[], EmailSenderPort]] = {
    "smtp": lambda: SMTPAdapter(
        host=notification_settings.smtp_host,
        port=notification_settings.smtp_port,
        username=notification_settings.smtp_username,
        password=notification_settings.smtp_password,
    )
}

_SMS_SENDERS: Dict[str, Callable[[], SMSSenderPort]] = {
    "noop": lambda: SMSAdapter(),
}

_PUSH_SENDERS: Dict[str, Callable[[], PushSenderPort]] = {
    "webhook": lambda: WebhookAdapter(endpoint=notification_settings.webhook_endpoint),
}

_WS_MANAGERS: Dict[str, Callable[[], ConnectionManagerPort]] = {
    "default": lambda: websocket_connection_manager,
}


def get_email_sender(provider: str | None = None) -> EmailSenderPort:
    key = (provider or notification_settings.email_provider or "smtp").lower()
    factory = _EMAIL_SENDERS.get(key) or _EMAIL_SENDERS["smtp"]
    return factory()


def get_sms_sender(provider: str | None = None) -> SMSSenderPort:
    key = (provider or notification_settings.sms_provider or "noop").lower()
    factory = _SMS_SENDERS.get(key) or _SMS_SENDERS["noop"]
    return factory()


def get_push_sender(provider: str | None = None) -> PushSenderPort:
    key = (provider or notification_settings.push_provider or "webhook").lower()
    factory = _PUSH_SENDERS.get(key) or _PUSH_SENDERS["webhook"]
    return factory()


def get_connection_manager() -> ConnectionManagerPort:
    return _WS_MANAGERS["default"]()


def get_auth_queries(db_session) -> UserReadService:
    """Constrói o serviço de leitura de usuário a partir do repositório SQLAlchemy."""
    user_repo = UserRepository(db=db_session)
    return AuthQueriesAdapter(user_read_service=user_repo)


__all__ = [
    "get_email_sender",
    "get_sms_sender",
    "get_push_sender",
    "get_connection_manager",
    "get_auth_queries",
]
