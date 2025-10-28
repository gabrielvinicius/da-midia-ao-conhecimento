"""Unit tests for MediaLifecycleService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from src.media_management.application.services import MediaLifecycleService
from src.media_management.domain.enums import MediaStatus


def _build_service(media_repo=None, delete_handler=None, reprocess_handler=None, access_policy=None):
    return MediaLifecycleService(
        media_repository=media_repo or AsyncMock(),
        delete_media_handler=delete_handler or AsyncMock(),
        reprocess_media_handler=reprocess_handler or AsyncMock(),
        access_policy=access_policy or MagicMock(),
    )


@pytest.mark.asyncio
async def test_delete_media_uses_policy_and_handler():
    access_policy = MagicMock()
    delete_handler = AsyncMock()
    media_repo = AsyncMock()
    media_repo.get_by_id.return_value = MagicMock()
    service = _build_service(media_repo=media_repo, delete_handler=delete_handler, access_policy=access_policy)

    media_id = UUID(int=1)
    user_id = UUID(int=2)

    await service.delete_media(media_id=media_id, user_id=user_id)

    access_policy.ensure_can_access.assert_called_once()
    delete_handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_reprocess_media_invokes_policy_and_handler():
    access_policy = MagicMock()
    reprocess_handler = AsyncMock()
    media_repo = AsyncMock()
    media_repo.get_by_id.return_value = MagicMock()
    service = _build_service(media_repo=media_repo, reprocess_handler=reprocess_handler, access_policy=access_policy)

    media_id = UUID(int=3)
    user_id = UUID(int=4)

    await service.reprocess_media(media_id=media_id, user_id=user_id)

    access_policy.ensure_can_access.assert_called_once()
    reprocess_handler.handle.assert_awaited_once()


@pytest.mark.asyncio
async def test_reset_for_reprocessing_updates_status_and_clears_error():
    media_repo = AsyncMock()
    existing_media = MagicMock(status=MediaStatus.FAILED)
    updated_media = MagicMock()

    media_repo.get_by_id.return_value = existing_media
    media_repo.update_status.return_value = updated_media

    service = _build_service(media_repo=media_repo)

    result = await service.reset_for_reprocessing(media_id=UUID(int=5))

    assert result is updated_media
    assert updated_media.error_message is None
    media_repo.save.assert_awaited_once_with(updated_media)


@pytest.mark.asyncio
async def test_update_status_persists_error_message():
    media_repo = AsyncMock()
    media_repo.get_by_id.return_value = MagicMock()
    updated_media = MagicMock()
    media_repo.update_status.return_value = updated_media

    service = _build_service(media_repo=media_repo)

    result = await service.update_status(
        media_id=UUID(int=6),
        status=MediaStatus.PROCESSING,
        error_message="boom",
    )

    assert result is updated_media
    assert updated_media.error_message == "boom"
    media_repo.save.assert_awaited_once_with(updated_media)
