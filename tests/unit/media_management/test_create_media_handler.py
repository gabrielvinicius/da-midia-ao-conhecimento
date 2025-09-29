# tests/unit/media_management/test_create_media_handler.py
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.media_management.application.commands.create_media_command import CreateMediaCommand
from src.media_management.application.commands.create_media_command_handler import CreateMediaCommandHandler
from src.media_management.domain.media import Media, MediaType
from src.shared.events.domain_events import MediaUploaded

@pytest.fixture
def handler_mocks():
    """Sets up mocks for the CreateMediaCommandHandler dependencies."""
    mock_storage_service = AsyncMock()
    return {
        "media_repository": AsyncMock(),
        "storage_service_factory": MagicMock(return_value=mock_storage_service),
        "event_bus": AsyncMock(),
        "mock_storage_service": mock_storage_service, # Return for assertion
    }

@pytest.mark.asyncio
async def test_create_media_for_video(handler_mocks):
    """Tests that uploading a video file correctly creates a VIDEO media entity and publishes an event."""
    # Arrange
    handler = CreateMediaCommandHandler(
        media_repository=handler_mocks["media_repository"],
        storage_service_factory=handler_mocks["storage_service_factory"],
        event_bus=handler_mocks["event_bus"],
    )
    command = CreateMediaCommand(
        user_id="user1",
        file=b"video_content",
        filename="my_awesome_video.mp4",
        storage_provider="local"
    )

    # Act
    result_media = await handler.handle(command)

    # Assert
    assert result_media.media_type == MediaType.VIDEO
    handler_mocks["mock_storage_service"].upload.assert_awaited_once()
    handler_mocks["media_repository"].save.assert_awaited_once()
    
    # Verify the published event
    handler_mocks["event_bus"].publish.assert_awaited_once()
    published_event: MediaUploaded = handler_mocks["event_bus"].publish.await_args.args[0]
    assert isinstance(published_event, MediaUploaded)
    assert published_event.media_id == str(result_media.id)
    assert published_event.media_type == MediaType.VIDEO

@pytest.mark.asyncio
async def test_create_media_for_audio(handler_mocks):
    """Tests that uploading an audio file correctly creates an AUDIO media entity."""
    # Arrange
    handler = CreateMediaCommandHandler(
        media_repository=handler_mocks["media_repository"],
        storage_service_factory=handler_mocks["storage_service_factory"],
        event_bus=handler_mocks["event_bus"],
    )
    command = CreateMediaCommand(
        user_id="user1",
        file=b"audio_content",
        filename="podcast_episode.mp3",
        storage_provider="s3"
    )

    # Act
    result_media = await handler.handle(command)

    # Assert
    assert result_media.media_type == MediaType.AUDIO
    assert result_media.storage_provider == "s3"
    handler_mocks["event_bus"].publish.assert_awaited_once()
