"""Lista única dos módulos que guardam dados de um usuário.

A ordem importa: as mídias primeiro (levam transcrições, análises e trechos
indexados), depois os avisos e as avaliações restantes; a conta sai por último.
"""
from __future__ import annotations

from typing import List

from src.media_management.application.services.media_service import MediaService
from src.media_management.infrastructure.adapters.user_media_eraser import UserMediaEraser
from src.media_management.infrastructure.repositories.media_repository import MediaRepository
from src.notifications.infrastructure.adapters.user_notifications_eraser import (
    UserNotificationsEraser,
)
from src.notifications.infrastructure.repositories.notification_repository import (
    NotificationRepository,
)
from src.text_analysis.infrastructure.adapters.user_feedback_eraser import UserFeedbackEraser
from src.text_analysis.infrastructure.repositories.feedback_repository import FeedbackRepository
from src.user_management.application.ports import UserDataEraserPort


def build_user_data_erasers(session, media_service: MediaService) -> List[UserDataEraserPort]:
    return [
        UserMediaEraser(MediaRepository(db=session), media_service.deletion),
        UserNotificationsEraser(NotificationRepository(db=session)),
        UserFeedbackEraser(FeedbackRepository(session)),
    ]


__all__ = ["build_user_data_erasers"]
