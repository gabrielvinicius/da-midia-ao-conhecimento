"""Avisos do usuário: a lista do sino e a marcação como lido.

Os avisos chegam em tempo real pelo WebSocket, mas ficam gravados: quem fecha
a página durante o processamento os encontra aqui ao voltar.
"""
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status

from src.notifications.application.dtos import (
    GetUserNotificationsQuery,
    MarkNotificationAsReadCommand,
)
from src.notifications.application.realtime import realtime_message
from src.user_management.api.dependencies import get_current_user
from src.user_management.domain import User

from ..application.services.notification_service import NotificationService
from .dependencies import get_notification_service

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/", summary="Avisos mais recentes do usuário")
async def list_my_notifications(
    limit: int = Query(30, ge=1, le=100),
    unread: bool = Query(False, description="Só os avisos ainda não lidos."),
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    notifications = await service.get_user_notifications(
        GetUserNotificationsQuery(user_id=current_user.id, limit=limit, include_read=not unread)
    )
    # Mesmo formato da mensagem do WebSocket: a interface trata os dois igual.
    return [realtime_message(n)["payload"] for n in notifications]


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT, summary="Marcar todos os avisos como lidos")
async def mark_all_my_notifications_as_read(
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> None:
    await service.mark_all_as_read(current_user.id)


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT, summary="Marcar um aviso como lido")
async def mark_notification_as_read(
    notification_id: UUID,
    service: NotificationService = Depends(get_notification_service),
    current_user: User = Depends(get_current_user),
) -> None:
    # Inexistente ou de outro usuário: 404, sem revelar qual (pelo serviço).
    await service.mark_notification_as_read(
        MarkNotificationAsReadCommand(notification_id=notification_id, user_id=current_user.id)
    )
