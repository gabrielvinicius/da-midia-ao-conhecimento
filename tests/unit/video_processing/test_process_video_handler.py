# tests/unit/video_processing/test_process_video_handler.py
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.media_management.domain.media import Media, MediaType
from src.media_processing.video_processing.application.commands.process_video_command import (
    ProcessVideoCommand,
)
from src.media_processing.video_processing.application.commands.process_video_command_handler import (
    ProcessVideoCommandHandler,
)
from src.shared.events.domain_events import AudioExtracted


@pytest.fixture
def handler_mocks():
    """Sets up mocks for the ProcessVideoCommandHandler dependencies."""
    mock_storage_service = AsyncMock()
    return {
        "media_queries": AsyncMock(),
        "storage_service_factory": MagicMock(return_value=mock_storage_service),
        "event_bus": AsyncMock(),
        "mock_storage_service": mock_storage_service, # Return for assertion
    }

@pytest.mark.asyncio
@patch("src.media_processing.video_processing.application.commands.process_video_command_handler.av")
async def test_process_video_handler_success(mock_av, handler_mocks):
    """Tests that the handler correctly extracts audio and publishes an event."""
    # Arrange
    media_id = str(uuid4())
    user_id = str(uuid4())
    original_path = f"media/{user_id}/{media_id}/video.mp4"
    media = Media(id=media_id, user_id=user_id, original_file_path=original_path, media_type=MediaType.VIDEO, storage_provider="local")

    handler_mocks["media_queries"].get_by_id.return_value = media
    handler_mocks["mock_storage_service"].download.return_value = b"fake_video_bytes"

    # Mock the PyAV library logic
    mock_av.open.return_value.__enter__.return_value.streams.audio = [MagicMock()]
    mock_av.open.return_value.__enter__.return_value.decode.return_value = [MagicMock()]
    mock_av.open.return_value.__exit__.return_value = None

    handler = ProcessVideoCommandHandler(**{k: v for k, v in handler_mocks.items() if k != "mock_storage_service"})
    command = ProcessVideoCommand(media_id=media_id, file_path=original_path)

    # Act
    await handler.handle(command)

    # Assert
    # 1. It downloaded the original video file
    handler_mocks["mock_storage_service"].download.assert_awaited_once_with(original_path)

    # 2. It uploaded the new audio file
    handler_mocks["mock_storage_service"].upload.assert_awaited_once()
    upload_args = handler_mocks["mock_storage_service"].upload.await_args.args
    assert upload_args[0].endswith(".mp3") # Check if the new file is an mp3
    assert isinstance(upload_args[1], bytes) # Check if it uploaded bytes

    # 3. It published the correct event
    handler_mocks["event_bus"].publish.assert_awaited_once()
    published_event: AudioExtracted = handler_mocks["event_bus"].publish.await_args.args[0]
    assert isinstance(published_event, AudioExtracted)
    assert published_event.media_id == media_id
    assert published_event.audio_file_path == upload_args[0]
