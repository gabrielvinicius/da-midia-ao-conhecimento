# tests/unit/media_management/test_media_service.py
"""Unit tests for the media service delegation logic."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from src.media_management.application.media_service import MediaService


@pytest.mark.asyncio
@pytest.mark.unit
async def test_media_service_create_media_delegates_to_command_handler():
    """Ensure MediaService delegates media creation to the command handler."""

    expected_media = object()

    create_handler = AsyncMock()
    create_handler.handle.return_value = expected_media

    service = MediaService(
        media_repo=AsyncMock(),
        media_queries=AsyncMock(),
        create_media_handler=create_handler,
        delete_media_handler=AsyncMock(),
        reprocess_media_handler=AsyncMock(),
        media_logger=AsyncMock(),
        media_metrics=AsyncMock(),
        media_settings=MagicMock(),
    )

    user_id = UUID(int=1)
    file_content = b"test-bytes"
    filename = "sample.mp3"
    storage_provider = "local"

    result = await service.create_media(
        user_id=user_id,
        file_content=file_content,
        filename=filename,
        storage_provider=storage_provider,
    )

    assert result is expected_media
    create_handler.handle.assert_awaited_once()

    command = create_handler.handle.await_args.args[0]
    assert command.user_id == str(user_id)
    assert command.file == file_content
    assert command.filename == filename
    assert command.storage_provider == storage_provider
