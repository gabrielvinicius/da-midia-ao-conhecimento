"""Unit tests for the consolidated MediaService."""

from __future__ import annotations

from typing import Dict
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.dtos import (
    CreateMediaCommand,
    DeleteMediaCommand,
    GetMediaStatisticsQuery,
    ReprocessMediaCommand,
)
from src.media_management.application.services.components import UploadResult
from src.media_management.application.services.media_read_service import (
    MediaReadService,
)
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.services.validators import MediaUploadValidator
from src.media_management.domain import Media
from src.media_management.infrastructure.metrics.prometheus_metrics import (
    PrometheusMediaMetrics,
)
from src.shared.domain.enums import MediaStatus, MediaType
from src.user_management.domain.entities.user import UserRole


@pytest.fixture()
def service_components() -> Dict[str, object]:
    media_repository = MagicMock()
    media_repository.db = None
    media_repository.get_by_id = AsyncMock()
    media_repository.delete = AsyncMock()
    media_repository.save = AsyncMock()
    media_repository.update = AsyncMock()
    media_repository.count_all = AsyncMock(return_value=7)
    media_repository.count_by_user = AsyncMock()
    media_repository.count_by_user_and_status = AsyncMock()
    media_repository.count_by_status = AsyncMock(
        side_effect=lambda status: 3 if status == MediaStatus.UPLOADED else 0
    )

    media_read_service = MediaReadService(media_repository=media_repository)
    storage_uploader = MagicMock()
    storage_uploader.upload = AsyncMock()
    metadata_mapper = MagicMock()
    metadata_mapper.map = MagicMock()
    metrics_service = MagicMock(spec=PrometheusMediaMetrics)
    upload_validator = MagicMock(spec=MediaUploadValidator)
    storage_maintenance = MagicMock()
    access_policy = MagicMock()

    service = MediaService(
        media_repository=media_repository,
        storage_uploader=storage_uploader,
        metadata_mapper=metadata_mapper,
        metrics_service=metrics_service,
        upload_validator=upload_validator,
        media_read_service=media_read_service,
        event_bus=None,
        emit_legacy_task=False,
        storage_maintenance=storage_maintenance,
    )
    service.access_policy = access_policy

    # Inject async storage_uploader stub
    async def _upload_stub(command, media_id, content_type):
        return UploadResult(
            destination_path=f"{command.user_id}/{media_id}/{command.filename}",
            metadata={},
        )
    storage_uploader.upload.side_effect = _upload_stub

    return {
        "service": service,
        "media_repository": media_repository,
        "media_read_service": media_read_service,
        "storage_uploader": storage_uploader,
        "metrics_service": metrics_service,
        "validator": upload_validator,
        "access_policy": access_policy,
    }


@pytest.mark.asyncio
async def test_upload_media_invokes_validator_and_handler(service_components):
    service: MediaService = service_components["service"]
    validator: MagicMock = service_components["validator"]
    validator.validate.return_value = None
    service.side_effect_publisher = MagicMock()
    service.side_effect_publisher.publish = AsyncMock(return_value={"id": "123"})

    cmd = CreateMediaCommand(
        user_id=uuid4(),
        file=b"bytes",
        filename="sample.mp4",
        storage_provider="local",
        transcription_provider="mock",
        summarization_provider="mock",
        sentiment_provider=None,
        topic_modeling_provider=None,
        metadata={},
    )

    result = await service.create_media(cmd)

    validator.validate.assert_called_once_with(b"bytes", "sample.mp4")
    service.side_effect_publisher.publish.assert_awaited()
    assert result.id


@pytest.mark.asyncio
async def test_delete_media_checks_access_and_dispatches(service_components):
    service: MediaService = service_components["service"]
    media_repository = service_components["media_repository"]
    access_policy = service_components["access_policy"]

    media = Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        filename="demo.mp4",
        file_size_bytes=123,
        media_type=MediaType.VIDEO,
        storage_provider="local",
        original_file_path="media/demo.mp4",
    )
    media_repository.get_by_id.return_value = media

    returned = await service.delete_media(
        DeleteMediaCommand(media_id=media.id),
        user_id=media.user_id,
        user_role=UserRole.USER,
    )

    access_policy.ensure_can_access.assert_called_once()
    media_repository.delete.assert_awaited_once()
    assert returned == media


@pytest.mark.asyncio
async def test_reprocess_media_allows_admin_without_user_id(service_components):
    service: MediaService = service_components["service"]
    media_repository = service_components["media_repository"]

    media = Media.create(
        media_id=uuid4(),
        user_id=uuid4(),
        filename="demo.mp4",
        file_size_bytes=123,
        original_file_path="media/demo.mp4",
        media_type=MediaType.AUDIO,
        storage_provider="local",
    )
    media_repository.get_by_id.return_value = media

    returned = await service.reprocess_media(
        ReprocessMediaCommand(media_id=media.id),
        user_id=None,
        user_role=UserRole.ADMIN,
    )

    assert returned == media


@pytest.mark.asyncio
async def test_get_media_statistics_scopes_by_user(service_components):
    service: MediaService = service_components["service"]

    stats = await service.get_media_statistics(GetMediaStatisticsQuery(user_id=None))

    assert stats["total"] == 7
    assert stats["by_status"][MediaStatus.UPLOADED.value] == 3
