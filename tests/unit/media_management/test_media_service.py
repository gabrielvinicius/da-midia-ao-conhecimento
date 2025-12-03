"""Unit tests for the consolidated MediaService."""

from __future__ import annotations

from typing import Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.media_management.application.services import MediaService
from src.shared.domain.enums import MediaStatus, MediaType
from src.media_management.domain.media import Media
from src.user_management.domain.user import UserRole


@pytest.fixture()
def service_components() -> Dict[str, object]:
    media_queries = MagicMock()
    media_queries.get_by_id = AsyncMock()
    media_queries.list_all = AsyncMock()
    media_queries.count_all = AsyncMock()
    media_queries.count_by_status = AsyncMock()
    media_queries.count_by_user = AsyncMock()
    media_queries.count_by_user_and_status = AsyncMock()

    create_handler = MagicMock()
    create_handler.handle = AsyncMock()
    delete_handler = MagicMock()
    delete_handler.handle = AsyncMock()
    reprocess_handler = MagicMock()
    reprocess_handler.handle = AsyncMock()

    validator = MagicMock()
    access_policy = MagicMock()

    service = MediaService(
        media_queries=media_queries,
        create_media_handler=create_handler,
        delete_media_handler=delete_handler,
        reprocess_media_handler=reprocess_handler,
        upload_validator=validator,
        access_policy=access_policy,
    )

    return {
        "service": service,
        "media_queries": media_queries,
        "create_handler": create_handler,
        "delete_handler": delete_handler,
        "reprocess_handler": reprocess_handler,
        "validator": validator,
        "access_policy": access_policy,
    }


@pytest.mark.asyncio
async def test_upload_media_invokes_validator_and_handler(service_components):
    service: MediaService = service_components["service"]
    validator: MagicMock = service_components["validator"]
    create_handler = service_components["create_handler"]
    create_handler.handle.return_value = {"id": "123"}

    result = await service.upload_media(
        user_id=uuid4(),
        file_content=b"bytes",
        filename="sample.mp4",
        storage_provider="local",
        transcription_provider="mock",
        summarization_provider="mock",
    )

    validator.validate.assert_called_once_with(b"bytes", "sample.mp4")
    create_handler.handle.assert_awaited_once()
    assert result == {"id": "123"}


@pytest.mark.asyncio
async def test_delete_media_checks_access_and_dispatches(service_components):
    service: MediaService = service_components["service"]
    media_queries = service_components["media_queries"]
    delete_handler = service_components["delete_handler"]
    access_policy = service_components["access_policy"]

    media = Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        original_file_path="media/demo.mp4",
        media_type=MediaType.VIDEO,
        storage_provider="local",
    )
    media_queries.get_by_id.return_value = media

    returned = await service.delete_media(
        media_id=media.id,
        user_id=media.user_id,
        user_role=UserRole.USER,
    )

    access_policy.ensure_can_access.assert_called_once()
    delete_handler.handle.assert_awaited_once()
    assert returned == media


@pytest.mark.asyncio
async def test_reprocess_media_allows_admin_without_user_id(service_components):
    service: MediaService = service_components["service"]
    media_queries = service_components["media_queries"]
    reprocess_handler = service_components["reprocess_handler"]

    media = Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        original_file_path="media/demo.mp4",
        media_type=MediaType.AUDIO,
        storage_provider="local",
    )
    media_queries.get_by_id.return_value = media

    returned = await service.reprocess_media(
        media_id=media.id,
        user_id=None,
        user_role=UserRole.ADMIN,
    )

    reprocess_handler.handle.assert_awaited_once()
    assert returned == media


@pytest.mark.asyncio
async def test_get_media_statistics_scopes_by_user(service_components):
    service: MediaService = service_components["service"]
    media_queries = service_components["media_queries"]

    media_queries.count_by_user.return_value = 7

    async def _count_by_user_and_status(user_id: UUID, status: MediaStatus) -> int:
        return 3 if status == MediaStatus.UPLOADED else 0

    media_queries.count_by_user_and_status.side_effect = _count_by_user_and_status

    stats = await service.get_media_statistics(user_id=uuid4())

    assert stats["total"] == 7
    assert stats["by_status"][MediaStatus.UPLOADED.value] == 3
