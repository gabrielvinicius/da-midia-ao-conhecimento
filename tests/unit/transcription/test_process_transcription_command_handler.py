# tests/unit/transcription/test_process_transcription_command_handler.py
"""
Unit tests for ProcessTranscriptionCommandHandler.
Tests the CQRS command handling pattern for transcription processing with comprehensive scenarios.
Validates event-driven architecture, real-time updates, and ML service integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, call
import json
from datetime import datetime

from src.transcription.application.commands.process_transcription_command_handler import ProcessTranscriptionCommandHandler
from src.transcription.application.commands.process_transcription_command import ProcessTranscriptionCommand
from src.media_management.domain.media import Media, MediaType, MediaStatus
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.shared.events.domain_events import TranscriptionStarted, TranscriptionCompleted, TranscriptionFailed
from src.shared.exceptions.domain_exceptions import ValidationError, ProcessingError


class TestProcessTranscriptionCommandHandler:
    """Test suite for ProcessTranscriptionCommandHandler following DDD and Event-Driven patterns."""

    @pytest.fixture
    def mock_dependencies(self, mock_speech_recognition_service, mock_storage_service, mock_event_bus, 
                         mock_transcription_repository, mock_media_queries, mock_media_repository,
                         mock_metrics_service, mock_connection_manager):
        """Complete set of mocked dependencies for ProcessTranscriptionCommandHandler."""
        return {
            "speech_recognition": mock_speech_recognition_service,
            "storage_service": mock_storage_service,
            "event_bus": mock_event_bus,
            "transcription_repository": mock_transcription_repository,
            "media_queries": mock_media_queries,
            "media_repository": mock_media_repository,
            "metrics_service": mock_metrics_service,
            "connection_manager": mock_connection_manager
        }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """ProcessTranscriptionCommandHandler instance with mocked dependencies."""
        return ProcessTranscriptionCommandHandler(**mock_dependencies)

    @pytest.fixture
    def valid_command(self, test_data_factory):
        """Valid ProcessTranscriptionCommand for testing."""
        command_data = test_data_factory.create_transcription_command_data()
        return ProcessTranscriptionCommand(
            media_id=command_data["media_id"],
            file_path=command_data["file_path"],
            storage_provider=command_data["storage_provider"],
            transcription_provider=command_data["transcription_provider"],
            language=command_data["language"]
        )

    @pytest.fixture
    def sample_media(self, test_data_factory, valid_command):
        """Sample media entity for testing."""
        return test_data_factory.create_audio_media(
            id=valid_command.media_id,
            user_id="user_123",
            status=MediaStatus.UPLOADED
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_transcription_with_realtime_updates(self, handler, mock_dependencies, 
                                                               valid_command, sample_media, test_data_factory):
        """Test successful transcription processing with WebSocket real-time updates."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
        mock_dependencies["storage_service"].download.return_value = (b"fake_audio_bytes", "audio/mp3")
        
        expected_transcription_text = "This is the transcribed text from the audio file."
        mock_dependencies["speech_recognition"].transcribe.return_value = {
            "text": expected_transcription_text,
            "segments": [
                {"start": 0.0, "end": 2.5, "text": "This is the transcribed", "confidence": 0.95},
                {"start": 2.5, "end": 5.0, "text": "text from the audio file.", "confidence": 0.89}
            ],
            "language": "en",
            "confidence": 0.92
        }
        
        created_transcription = test_data_factory.create_transcription(
            media_id=valid_command.media_id,
            text=expected_transcription_text
        )
        mock_dependencies["transcription_repository"].save.return_value = created_transcription

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.text == expected_transcription_text
        assert result.status == TranscriptionStatus.COMPLETED
        assert result.language == "en"
        
        # Verify real-time updates were sent
        assert mock_dependencies["connection_manager"].send_personal_message.call_count >= 3
        
        # Verify media status update to PROCESSING
        calls = mock_dependencies["connection_manager"].send_personal_message.call_args_list
        media_update_call = calls[0]
        media_message = json.loads(media_update_call.args[0])
        assert media_message["type"] == "entity_update"
        assert media_message["entity"] == "media"
        assert media_message["payload"]["status"] == "PROCESSING"
        
        # Verify transcription started update
        transcription_start_call = calls[1]
        start_message = json.loads(transcription_start_call.args[0])
        assert start_message["type"] == "entity_update"
        assert start_message["entity"] == "transcription"
        assert start_message["payload"]["status"] == "PROCESSING"
        
        # Verify transcription completed update
        transcription_complete_call = calls[2]
        complete_message = json.loads(transcription_complete_call.args[0])
        assert complete_message["type"] == "entity_update"
        assert complete_message["entity"] == "transcription"
        assert complete_message["payload"]["status"] == "COMPLETED"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_with_speaker_diarization(self, handler, mock_dependencies, 
                                                        valid_command, sample_media, test_data_factory):
        """Test transcription processing with speaker diarization enabled."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
        mock_dependencies["storage_service"].download.return_value = (b"fake_audio_bytes", "audio/mp3")
        
        # Mock speech recognition with speaker information
        mock_dependencies["speech_recognition"].transcribe.return_value = {
            "text": "Speaker 1: Hello there. Speaker 2: Hi, how are you?",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Hello there", "speaker": "Speaker 1", "confidence": 0.95},
                {"start": 2.5, "end": 4.5, "text": "Hi, how are you?", "speaker": "Speaker 2", "confidence": 0.91}
            ],
            "speakers": ["Speaker 1", "Speaker 2"],
            "language": "en",
            "confidence": 0.93
        }
        
        created_transcription = test_data_factory.create_transcription(
            media_id=valid_command.media_id,
            speakers=["Speaker 1", "Speaker 2"]
        )
        mock_dependencies["transcription_repository"].save.return_value = created_transcription

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert len(result.speakers) == 2
        assert "Speaker 1" in result.speakers
        assert "Speaker 2" in result.speakers
        assert len(result.segments) == 2
        assert result.segments[0]["speaker"] == "Speaker 1"
        assert result.segments[1]["speaker"] == "Speaker 2"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_already_exists_skip_processing(self, handler, mock_dependencies, 
                                                             valid_command, sample_media, test_data_factory):
        """Test that existing transcription is returned without reprocessing."""
        # Arrange
        existing_transcription = test_data_factory.create_transcription(
            media_id=valid_command.media_id,
            status=TranscriptionStatus.COMPLETED,
            text="Existing transcription text"
        )
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = existing_transcription

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result == existing_transcription
        assert result.text == "Existing transcription text"
        
        # Verify that speech recognition was not called
        mock_dependencies["speech_recognition"].transcribe.assert_not_awaited()
        mock_dependencies["storage_service"].download.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_media_not_found(self, handler, mock_dependencies, valid_command):
        """Test error handling when media is not found."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValidationError, match="Media not found"):
            await handler.handle(valid_command)
        
        mock_dependencies["speech_recognition"].transcribe.assert_not_awaited()
        mock_dependencies["transcription_repository"].save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_unsupported_media_type(self, handler, mock_dependencies, 
                                                      valid_command, test_data_factory):
        """Test error handling for unsupported media types."""
        # Arrange
        text_media = test_data_factory.create_media(
            id=valid_command.media_id,
            media_type=MediaType.TEXT,  # Unsupported for transcription
            user_id="user_123"
        )
        mock_dependencies["media_queries"].get_by_id.return_value = text_media

        # Act & Assert
        with pytest.raises(ValidationError, match="Media type not supported for transcription"):
            await handler.handle(valid_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_storage_download_failure(self, handler, mock_dependencies, 
                                                        valid_command, sample_media):
        """Test error handling when storage download fails."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
        mock_dependencies["storage_service"].download.side_effect = Exception("Storage service unavailable")

        # Act & Assert
        with pytest.raises(ProcessingError, match="Failed to download media file"):
            await handler.handle(valid_command)
        
        mock_dependencies["speech_recognition"].transcribe.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_speech_recognition_failure(self, handler, mock_dependencies, 
                                                          valid_command, sample_media):
        """Test error handling when speech recognition fails."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
        mock_dependencies["storage_service"].download.return_value = (b"fake_audio_bytes", "audio/mp3")
        mock_dependencies["speech_recognition"].transcribe.side_effect = Exception("ML service error")

        # Act & Assert
        with pytest.raises(ProcessingError, match="Speech recognition failed"):
            await handler.handle(valid_command)
        
        # Verify TranscriptionFailed event was published
        mock_dependencies["event_bus"].publish.assert_awaited()
        published_event = mock_dependencies["event_bus"].publish.await_args.args[0]
        assert isinstance(published_event, TranscriptionFailed)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_events_publishing(self, handler, mock_dependencies, 
                                                 valid_command, sample_media, test_data_factory):
        """Test that appropriate domain events are published during transcription."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
        mock_dependencies["storage_service"].download.return_value = (b"fake_audio_bytes", "audio/mp3")
        mock_dependencies["speech_recognition"].transcribe.return_value = {
            "text": "Test transcription",
            "segments": [],
            "language": "en",
            "confidence": 0.9
        }
        
        created_transcription = test_data_factory.create_transcription(media_id=valid_command.media_id)
        mock_dependencies["transcription_repository"].save.return_value = created_transcription

        # Act
        await handler.handle(valid_command)

        # Assert
        # Should publish TranscriptionStarted and TranscriptionCompleted events
        assert mock_dependencies["event_bus"].publish.call_count >= 2
        
        published_events = [call.args[0] for call in mock_dependencies["event_bus"].publish.call_args_list]
        event_types = [type(event) for event in published_events]
        
        assert TranscriptionStarted in event_types
        assert TranscriptionCompleted in event_types

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_multiple_languages(self, handler, mock_dependencies, test_data_factory):
        """Test transcription processing with different languages."""
        languages = ["en", "pt", "es", "fr"]
        
        for language in languages:
            # Arrange
            command = ProcessTranscriptionCommand(
                media_id=f"media_{language}",
                file_path=f"/uploads/audio_{language}.mp3",
                storage_provider="local",
                transcription_provider="whisper",
                language=language
            )
            
            sample_media = test_data_factory.create_audio_media(id=command.media_id)
            mock_dependencies["media_queries"].get_by_id.return_value = sample_media
            mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
            mock_dependencies["storage_service"].download.return_value = (b"fake_audio_bytes", "audio/mp3")
            mock_dependencies["speech_recognition"].transcribe.return_value = {
                "text": f"Sample text in {language}",
                "segments": [],
                "language": language,
                "confidence": 0.85
            }
            
            created_transcription = test_data_factory.create_transcription(
                media_id=command.media_id,
                language=language
            )
            mock_dependencies["transcription_repository"].save.return_value = created_transcription

            # Act
            result = await handler.handle(command)

            # Assert
            assert result.language == language

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_confidence_scoring(self, handler, mock_dependencies, 
                                                  valid_command, sample_media, test_data_factory):
        """Test that confidence scores are properly handled and stored."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
        mock_dependencies["storage_service"].download.return_value = (b"fake_audio_bytes", "audio/mp3")
        
        # Mock low confidence transcription
        mock_dependencies["speech_recognition"].transcribe.return_value = {
            "text": "Low confidence transcription",
            "segments": [
                {"start": 0.0, "end": 2.0, "text": "Low confidence", "confidence": 0.65},
                {"start": 2.0, "end": 4.0, "text": "transcription", "confidence": 0.55}
            ],
            "language": "en",
            "confidence": 0.60  # Low overall confidence
        }
        
        created_transcription = test_data_factory.create_transcription(
            media_id=valid_command.media_id,
            confidence_score=0.60
        )
        mock_dependencies["transcription_repository"].save.return_value = created_transcription

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.confidence_score == 0.60
        assert all(segment["confidence"] < 0.7 for segment in result.segments)
        
        # Verify that low confidence warning was logged/handled
        saved_transcription = mock_dependencies["transcription_repository"].save.await_args.args[0]
        assert saved_transcription.confidence_score == 0.60

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_transcription_metrics_recording(self, handler, mock_dependencies, 
                                                 valid_command, sample_media, test_data_factory):
        """Test that performance metrics are properly recorded."""
        # Arrange
        mock_dependencies["media_queries"].get_by_id.return_value = sample_media
        mock_dependencies["transcription_repository"].find_by_media_id.return_value = None
        mock_dependencies["storage_service"].download.return_value = (b"fake_audio_bytes", "audio/mp3")
        mock_dependencies["speech_recognition"].transcribe.return_value = {
            "text": "Test transcription",
            "segments": [],
            "language": "en",
            "confidence": 0.9
        }
        
        created_transcription = test_data_factory.create_transcription(
            media_id=valid_command.media_id,
            processing_time=5.2
        )
        mock_dependencies["transcription_repository"].save.return_value = created_transcription

        # Act
        await handler.handle(valid_command)

        # Assert
        # Verify metrics were recorded
        mock_dependencies["metrics_service"].increment_counter.assert_called()
        mock_dependencies["metrics_service"].record_histogram.assert_called()
        
        # Check specific metrics calls
        counter_calls = [call.args[0] for call in mock_dependencies["metrics_service"].increment_counter.call_args_list]
        assert "transcription.started" in counter_calls
        assert "transcription.completed" in counter_calls
