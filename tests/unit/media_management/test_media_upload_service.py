"""Unit tests for MediaUploadService."""

from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.media_management.application.services import MediaUploadService


@pytest.mark.asyncio
async def test_media_upload_service_validates_and_dispatches():
    validator = MagicMock()
    handler = AsyncMock()
    expected_result = {"id": "123"}
    handler.handle.return_value = expected_result

    service = MediaUploadService(create_media_handler=handler, upload_validator=validator)

    user_id = UUID(int=1)
    file_content = b"bytes"
    filename = "sample.mp3"

    result = await service.create_media(
        user_id=user_id,
        file_content=file_content,
        filename=filename,
        storage_provider="local",
        transcription_provider="mock",
        summarization_provider="mock",
    )

    validator.validate.assert_called_once_with(file_content, filename)
    handler.handle.assert_awaited_once()
    assert result is expected_result
