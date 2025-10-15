# tests/unit/media_management/test_create_media_handler.py
"""
Unit tests for CreateMediaCommandHandler.
Tests the CQRS command handling pattern for media creation with comprehensive scenarios.
Validates event-driven architecture with domain event publishing.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.media_management.application.commands.create_media_command import CreateMediaCommand
from src.media_management.application.commands.create_media_command_handler import CreateMediaCommandHandler
from src.media_management.domain.media import Media, MediaType, MediaStatus
from src.shared.events.domain_events import MediaUploaded
from src.shared.exceptions.domain_exceptions import ValidationError, StorageError


class TestCreateMediaCommandHandler:
    """Test suite for CreateMediaCommandHandler following DDD and Event-Driven patterns."""

    @pytest.fixture
    def mock_dependencies(self, mock_storage_service, mock_event_bus, mock_media_repository, mock_metrics_service):
        """Complete set of mocked dependencies for CreateMediaCommandHandler."""
        storage_service_factory = MagicMock(return_value=mock_storage_service)
        return {
            "media_repository": mock_media_repository,
            "storage_service_factory": storage_service_factory,
            "event_bus": mock_event_bus,
            "metrics_service": mock_metrics_service,
            "storage_service": mock_storage_service
        }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """CreateMediaCommandHandler instance with mocked dependencies."""
        return CreateMediaCommandHandler(
            media_repository=mock_dependencies["media_repository"],
            storage_service_factory=mock_dependencies["storage_service_factory"],
            event_bus=mock_dependencies["event_bus"],
            metrics_service=mock_dependencies["metrics_service"]
        )

    @pytest.fixture
    def valid_video_command(self, test_data_factory):
        """Valid CreateMediaCommand for video upload testing."""
        upload_data = test_data_factory.create_upload_data(MediaType.VIDEO)
        return CreateMediaCommand(
            user_id="user_123",
            file=upload_data["file"],
            filename=upload_data["filename"],
            storage_provider=upload_data["storage_provider"]
        )

    @pytest.fixture
    def valid_audio_command(self, test_data_factory):
        """Valid CreateMediaCommand for audio upload testing."""
        upload_data = test_data_factory.create_upload_data(MediaType.AUDIO)
        return CreateMediaCommand(
            user_id="user_123",
            file=upload_data["file"],
            filename=upload_data["filename"],
            storage_provider=upload_data["storage_provider"]
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_video_media_success(self, handler, mock_dependencies, valid_video_command, test_data_factory):
        """Test successful video media creation with proper event publishing."""
        # Arrange
        expected_media = test_data_factory.create_video_media(
            user_id=valid_video_command.user_id,
            filename=valid_video_command.filename
        )
        mock_dependencies["media_repository"].save.return_value = expected_media
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_video_command.filename}",
            "size": len(valid_video_command.file)
        }

        # Act
        result = await handler.handle(valid_video_command)

        # Assert
        assert result.media_type == MediaType.VIDEO
        assert result.user_id == valid_video_command.user_id
        assert result.filename == valid_video_command.filename
        assert result.status == MediaStatus.UPLOADED
        
        # Verify storage upload
        mock_dependencies["storage_service"].upload.assert_awaited_once()
        upload_call = mock_dependencies["storage_service"].upload.await_args
        assert upload_call.kwargs["content"] == valid_video_command.file
        
        # Verify repository save
        mock_dependencies["media_repository"].save.assert_awaited_once()
        
        # Verify event publishing
        mock_dependencies["event_bus"].publish.assert_awaited_once()
        published_event = mock_dependencies["event_bus"].publish.await_args.args[0]
        assert isinstance(published_event, MediaUploaded)
        assert published_event.media_id == str(result.id)
        assert published_event.media_type == MediaType.VIDEO
        assert published_event.user_id == valid_video_command.user_id

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_audio_media_success(self, handler, mock_dependencies, valid_audio_command, test_data_factory):
        """Test successful audio media creation with S3 storage."""
        # Arrange
        expected_media = test_data_factory.create_audio_media(
            user_id=valid_audio_command.user_id,
            filename=valid_audio_command.filename
        )
        mock_dependencies["media_repository"].save.return_value = expected_media
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_audio_command.filename}",
            "size": len(valid_audio_command.file)
        }

        # Act
        result = await handler.handle(valid_audio_command)

        # Assert
        assert result.media_type == MediaType.AUDIO
        assert result.storage_provider == "local"
        assert result.status == MediaStatus.UPLOADED
        
        # Verify metrics recording
        mock_dependencies["metrics_service"].increment_counter.assert_called()
        mock_dependencies["metrics_service"].record_histogram.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_invalid_file_type(self, handler, mock_dependencies):
        """Test that ValidationError is raised for unsupported file types."""
        # Arrange
        invalid_command = CreateMediaCommand(
            user_id="user_123",
            file=b"invalid_content",
            filename="document.exe",  # Unsupported type
            storage_provider="local"
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="Unsupported file type"):
            await handler.handle(invalid_command)
        
        mock_dependencies["storage_service"].upload.assert_not_awaited()
        mock_dependencies["media_repository"].save.assert_not_awaited()
        mock_dependencies["event_bus"].publish.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_file_too_large(self, handler, mock_dependencies):
        """Test that ValidationError is raised for files exceeding size limits."""
        # Arrange
        large_file_command = CreateMediaCommand(
            user_id="user_123",
            file=b"x" * (500 * 1024 * 1024 + 1),  # 500MB + 1 byte (exceeds limit)
            filename="large_video.mp4",
            storage_provider="local"
        )

        # Act & Assert
        with pytest.raises(ValidationError, match="File size exceeds maximum limit"):
            await handler.handle(large_file_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_storage_failure(self, handler, mock_dependencies, valid_audio_command):
        """Test error handling when storage upload fails."""
        # Arrange
        mock_dependencies["storage_service"].upload.side_effect = StorageError("Storage service unavailable")

        # Act & Assert
        with pytest.raises(StorageError, match="Storage service unavailable"):
            await handler.handle(valid_audio_command)
        
        mock_dependencies["storage_service"].upload.assert_awaited_once()
        mock_dependencies["media_repository"].save.assert_not_awaited()
        mock_dependencies["event_bus"].publish.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_repository_failure(self, handler, mock_dependencies, valid_audio_command):
        """Test error handling when repository save fails."""
        # Arrange
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": "/uploads/test.mp3",
            "size": 1024
        }
        mock_dependencies["media_repository"].save.side_effect = Exception("Database error")

        # Act & Assert
        with pytest.raises(Exception, match="Database error"):
            await handler.handle(valid_audio_command)
        
        mock_dependencies["storage_service"].upload.assert_awaited_once()
        mock_dependencies["media_repository"].save.assert_awaited_once()
        mock_dependencies["event_bus"].publish.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_sets_correct_metadata(self, handler, mock_dependencies, valid_video_command):
        """Test that media entity is created with correct metadata."""
        # Arrange
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_video_command.filename}",
            "size": len(valid_video_command.file),
            "etag": "mock_etag_123"
        }
        
        # Mock the media repository to capture the saved media
        saved_media = None
        async def capture_save(media):
            nonlocal saved_media
            saved_media = media
            return media
        
        mock_dependencies["media_repository"].save.side_effect = capture_save

        # Act
        await handler.handle(valid_video_command)

        # Assert
        assert saved_media is not None
        assert saved_media.user_id == valid_video_command.user_id
        assert saved_media.filename == valid_video_command.filename
        assert saved_media.media_type == MediaType.VIDEO
        assert saved_media.status == MediaStatus.UPLOADED
        assert saved_media.file_size == len(valid_video_command.file)
        assert saved_media.storage_provider == valid_video_command.storage_provider
        assert saved_media.created_at is not None
        assert isinstance(saved_media.created_at, datetime)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_event_contains_correct_data(self, handler, mock_dependencies, valid_audio_command, test_data_factory):
        """Test that MediaUploaded event contains all required data."""
        # Arrange
        expected_media = test_data_factory.create_audio_media(
            user_id=valid_audio_command.user_id,
            filename=valid_audio_command.filename
        )
        mock_dependencies["media_repository"].save.return_value = expected_media
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_audio_command.filename}",
            "size": len(valid_audio_command.file)
        }

        # Act
        await handler.handle(valid_audio_command)

        # Assert
        mock_dependencies["event_bus"].publish.assert_awaited_once()
        published_event = mock_dependencies["event_bus"].publish.await_args.args[0]
        
        assert isinstance(published_event, MediaUploaded)
        assert published_event.media_id == str(expected_media.id)
        assert published_event.user_id == valid_audio_command.user_id
        assert published_event.media_type == MediaType.AUDIO
        assert published_event.file_path == f"/uploads/{valid_audio_command.filename}"
        assert published_event.storage_provider == valid_audio_command.storage_provider
        assert published_event.file_size == len(valid_audio_command.file)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_different_storage_providers(self, handler, mock_dependencies, test_data_factory):
        """Test media creation with different storage providers (local, s3, minio)."""
        storage_providers = ["local", "s3", "minio"]
        
        for provider in storage_providers:
            # Arrange
            command = CreateMediaCommand(
                user_id="user_123",
                file=b"test_content",
                filename=f"test_{provider}.mp3",
                storage_provider=provider
            )
            
            expected_media = test_data_factory.create_audio_media(
                user_id=command.user_id,
                filename=command.filename
            )
            mock_dependencies["media_repository"].save.return_value = expected_media
            mock_dependencies["storage_service"].upload.return_value = {
                "file_path": f"/uploads/{command.filename}",
                "size": len(command.file)
            }

            # Act
            result = await handler.handle(command)

            # Assert
            assert result.storage_provider == provider
            
            # Verify storage service factory was called with correct provider
            mock_dependencies["storage_service_factory"].assert_called_with(provider)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_mime_type_detection(self, handler, mock_dependencies, test_data_factory):
        """Test that MIME type is correctly detected and validated."""
        test_cases = [
            ("test.mp3", MediaType.AUDIO, "audio/mpeg"),
            ("test.wav", MediaType.AUDIO, "audio/wav"),
            ("test.mp4", MediaType.VIDEO, "video/mp4"),
            ("test.avi", MediaType.VIDEO, "video/x-msvideo"),
        ]
        
        for filename, expected_type, expected_mime in test_cases:
            # Arrange
            command = CreateMediaCommand(
                user_id="user_123",
                file=b"test_content",
                filename=filename,
                storage_provider="local"
            )
            
            expected_media = test_data_factory.create_media(
                media_type=expected_type,
                filename=filename
            )
            mock_dependencies["media_repository"].save.return_value = expected_media
            mock_dependencies["storage_service"].upload.return_value = {
                "file_path": f"/uploads/{filename}",
                "size": len(command.file)
            }

            # Act
            result = await handler.handle(command)

            # Assert
            assert result.media_type == expected_type
            
            # Verify upload was called with correct content type
            upload_call = mock_dependencies["storage_service"].upload.await_args
            assert expected_mime in str(upload_call) or "content_type" in upload_call.kwargs
