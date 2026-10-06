"""Ao conectar, o usuário recebe os avisos pendentes no formato em tempo real."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.notifications.application.services.notification_service import NotificationService
from src.notifications.domain import Notification


@pytest.mark.asyncio
async def test_only_what_was_sent_is_marked_as_delivered():
    user_id = uuid4()
    first, second = Notification(user_id=user_id, content="um"), Notification(user_id=user_id, content="dois")
    repo = MagicMock()
    repo.list_undelivered_by_user = AsyncMock(return_value=[first, second])
    repo.mark_as_delivered = AsyncMock()
    sent = []

    async def send(message):
        sent.append(message)
        return message["payload"]["content"] == "um"  # o segundo falha (conexão caiu)

    delivered = await NotificationService(repo).deliver_pending(user_id, send)

    assert delivered == 1
    assert [m["kind"] for m in sent] == ["new_notification", "new_notification"]
    repo.mark_as_delivered.assert_awaited_once_with(first.id)
