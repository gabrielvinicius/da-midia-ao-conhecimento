"""Unit tests for MediaLifecycleService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.media_management.application.services import MediaLifecycleService
from src.media_management.domain.enums import MediaStatus, MediaType
from src.media_management.domain.media import Media


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
    existing_media = Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        original_file_path="/tmp/file.mp4",
        media_type=MediaType.VIDEO,
        storage_provider="local",
        status=MediaStatus.FAILED,
    ).mark_failed("boom")
    updated_media = existing_media.with_status(MediaStatus.UPLOADED, error_message=None)

    media_repo.get_by_id.return_value = existing_media
    media_repo.update_status.return_value = updated_media

    service = _build_service(media_repo=media_repo)

    result = await service.reset_for_reprocessing(media_id=UUID(int=5))

    assert result == updated_media
    assert result.error_message is None
    media_repo.save.assert_awaited_once_with(updated_media)


@pytest.mark.asyncio
async def test_update_status_persists_error_message():
    media_repo = AsyncMock()
    media_repo.get_by_id.return_value = Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        original_file_path="/tmp/file.mp4",
        media_type=MediaType.VIDEO,
        storage_provider="local",
    )
    updated_media = media_repo.get_by_id.return_value.with_status(
        MediaStatus.PROCESSING,
        error_message="boom",
    )
    media_repo.update_status.return_value = updated_media

    service = _build_service(media_repo=media_repo)

    result = await service.update_status(
        media_id=UUID(int=6),
        status=MediaStatus.PROCESSING,
        error_message="boom",
    )

    assert result == updated_media
    assert result.error_message == "boom"
    media_repo.save.assert_awaited_once_with(updated_media)
