import pytest
from unittest.mock import AsyncMock, MagicMock, call
import json

from src.transcription.application.commands.process_transcription_command_handler import ProcessTranscriptionCommandHandler
from src.transcription.application.commands.process_transcription_command import ProcessTranscriptionCommand
from src.media_management.domain.media import Media
from src.transcription.domain.transcription import Transcription, TranscriptionStatus

# Mark the test as asynchronous
@pytest.mark.asyncio
async def test_handle_sends_realtime_updates():
    """Ensures the handler sends WebSocket updates at key processing stages."""
    # 1. Arrange: Mock all dependencies
    mock_speech_recognition = AsyncMock()
    mock_speech_recognition.transcribe.return_value = "This is the transcribed text."

    mock_storage_service = AsyncMock()
    mock_storage_service.download.return_value = (b"fake_audio_bytes", "audio/mp3")

    mock_event_bus = AsyncMock()
    mock_transcription_repo = AsyncMock()
    mock_media_queries = AsyncMock()
    mock_media_repository = AsyncMock()
    mock_metrics_service = MagicMock()
    mock_connection_manager = AsyncMock() # The most important mock for this test

    # Mock the return value for the media object
    fake_media = Media(id="media123", user_id="user123", original_file_path="path/to/file.mp4")
    mock_media_queries.get_by_id.return_value = fake_media

    # Mock the transcription repository to simulate finding no existing transcription
    mock_transcription_repo.find_by_media_id.return_value = None

    # Instantiate the handler with mocked dependencies
    handler = ProcessTranscriptionCommandHandler(
        speech_recognition=mock_speech_recognition,
        storage_service=mock_storage_service,
        event_bus=mock_event_bus,
        transcription_repository=mock_transcription_repo,
        media_queries=mock_media_queries,
        media_repository=mock_media_repository,
        metrics_service=mock_metrics_service,
        connection_manager=mock_connection_manager,
    )

    command = ProcessTranscriptionCommand(
        media_id="media123",
        file_path="path/to/file.mp4",
        storage_provider="local",
        transcription_provider="whisper",
        language="en",
    )

    # 2. Act: Execute the handler
    await handler.handle(command)

    # 3. Assert: Verify that send_personal_message was called at the correct times
    assert mock_connection_manager.send_personal_message.call_count >= 3

    # Check the first call: Media status updated to PROCESSING
    media_processing_call = mock_connection_manager.send_personal_message.call_args_list[0]
    args, _ = media_processing_call
    message_data = json.loads(args[0])
    assert message_data["type"] == "entity_update"
    assert message_data["entity"] == "media"
    assert message_data["payload"]["status"] == "PROCESSING"

    # Check the second call: Transcription status updated to PROCESSING
    transcription_processing_call = mock_connection_manager.send_personal_message.call_args_list[1]
    args, _ = transcription_processing_call
    message_data = json.loads(args[0])
    assert message_data["type"] == "entity_update"
    assert message_data["entity"] == "transcription"
    assert message_data["payload"]["status"] == "PROCESSING"

    # Check the third call: Transcription status updated to COMPLETED
    transcription_completed_call = mock_connection_manager.send_personal_message.call_args_list[2]
    args, _ = transcription_completed_call
    message_data = json.loads(args[0])
    assert message_data["type"] == "entity_update"
    assert message_data["entity"] == "transcription"
    assert message_data["payload"]["status"] == "COMPLETED"
