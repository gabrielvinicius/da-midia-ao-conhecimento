"""Avisos do usuário vistos pela API: a lista do sino e a marcação como lido.

A criação e a entrega dos avisos ficam com o PipelineNotificationService, que
os workers usam ao fim de cada etapa.
"""
from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, List
from uuid import UUID

from src.notifications.application.ports import NotificationRepositoryPort
from src.notifications.application.realtime import realtime_message
from src.notifications.domain import Notification

from ..dtos import GetUserNotificationsQuery, MarkNotificationAsReadCommand


Sender = Callable[[Dict[str, Any]], Awaitable[bool]]


class NotificationService:
    def __init__(self, notification_repo: NotificationRepositoryPort) -> None:
        self.repo = notification_repo

    async def get_user_notifications(self, query: GetUserNotificationsQuery) -> List[Notification]:
        return await self.repo.list_by_user(
            str(query.user_id), limit=query.limit, unread_only=not query.include_read
        )

    async def mark_notification_as_read(self, command: MarkNotificationAsReadCommand) -> bool:
        """Marca como lido; False se o aviso não existe ou é de outro usuário."""
        notification = await self.repo.find_by_id(command.notification_id)
        if not notification or notification.user_id != command.user_id:
            return False
        notification.mark_as_opened()
        await self.repo.save(notification)
        return True

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """Marca como lidos todos os avisos do usuário; devolve quantos mudaram."""
        return await self.repo.mark_all_as_read(str(user_id))

    async def deliver_pending(self, user_id: UUID, send: Sender, limit: int = 50) -> int:
        """Ao conectar, entrega o que chegou com a página fechada.

        Cada aviso vai no mesmo formato das mensagens em tempo real; só é
        marcado como entregue se o envio deu certo. Antes, a consulta chamava
        um método inexistente e a conexão era fechada logo após abrir.
        """
        delivered = 0
        for notification in await self.repo.list_undelivered_by_user(str(user_id), limit=limit):
            if await send(realtime_message(notification)):
                await self.repo.mark_as_delivered(notification.id)
                delivered += 1
        return delivered


__all__ = ["NotificationService"]
