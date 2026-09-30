"""O frontend só reconhece mensagens no formato {"kind": "new_notification", ...}.

Antes, API e workers enviavam {"type": "WEBSOCKET", ...}, que o cliente
descartava como tipo desconhecido: nenhum aviso em tempo real aparecia.
"""
import pytest
from uuid import uuid4

from src.notifications.application.realtime import notification_id_of, realtime_message
from src.notifications.application.services.pipeline_notification_service import (
    PipelineNotificationService,
)
from src.notifications.domain import Notification, NotificationType
from src.text_analysis.tasks import completion_message


class FakeRepo:
    async def save(self, notification):
        return notification


class NoOpLogger:
    async def log_operation(self, **kwargs):
        return None

    def info(self, *args, **kwargs):
        return None

    def warning(self, *args, **kwargs):
        return None

    def error(self, *args, **kwargs):
        return None


class NoOpMetrics:
    async def record_notification_sent(self, channel):
        return None


class RecordingDelivery:
    def __init__(self):
        self.sent = []

    async def send_to_user(self, user_id, payload):
        self.sent.append((user_id, payload))
        return True


def test_realtime_message_has_envelope_and_rest_fields():
    notification = Notification(
        user_id=uuid4(),
        type=NotificationType.WEBSOCKET,
        content="Análise concluída.",
        variables={"media_id": "m1", "evento": "TextAnalysisCompleted"},
    )

    message = realtime_message(notification)

    assert message["kind"] == "new_notification"
    payload = message["payload"]
    assert payload["id"] == str(notification.id)
    assert payload["content"] == "Análise concluída."
    assert payload["variables"]["media_id"] == "m1"
    assert payload["read"] is False
    assert notification_id_of(message) == str(notification.id)


@pytest.mark.asyncio
async def test_pipeline_notification_uses_realtime_envelope():
    delivery = RecordingDelivery()
    service = PipelineNotificationService(
        notification_repo=FakeRepo(),
        delivery=delivery,
        notification_logger=NoOpLogger(),
        notification_metrics=NoOpMetrics(),
    )
    user_id = uuid4()

    await service.notify(
        user_id=user_id,
        message="Transcrição concluída com sucesso.",
        variables={"media_id": "m1"},
    )

    (sent_user, message), = delivery.sent
    assert sent_user == user_id
    assert message["kind"] == "new_notification"
    assert message["payload"]["variables"]["media_id"] == "m1"


def test_completion_message_mentions_failed_steps():
    ok = {"diagnostics": {"steps": {"sentiment": "ok", "synthesis": "ok"}}}
    partial = {"diagnostics": {"steps": {"sentiment": "ok", "visual_insight": "failed: timeout"}}}

    assert completion_message(ok) == "Análise concluída. O resumo já está disponível."
    assert "visual_insight" in completion_message(partial)
    assert "sentiment" not in completion_message(partial)
