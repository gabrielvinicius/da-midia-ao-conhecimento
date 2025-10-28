"""Unit tests for the CreateMediaCommandHandler collaboration flow."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.media_management.application.commands.create_media_command import CreateMediaCommand
from src.media_management.application.commands.create_media_command_handler import CreateMediaCommandHandler
from src.media_management.domain.media import Media, MediaStatus, MediaType
from src.shared.exceptions.domain_exceptions import StorageError, ValidationError


class TestCreateMediaCommandHandler:
    """Ensures the handler coordinates explicit collaborators correctly."""

    @pytest.fixture
    def mock_dependencies(self, mock_storage_service, mock_media_repository):
        """Complete set of mocked collaborators for the handler."""

        storage_resolver = MagicMock()
        storage_resolver.resolve.return_value = mock_storage_service

        metrics_publisher = AsyncMock()
        event_publisher = AsyncMock()
        file_validator = MagicMock()
        file_validator.validate.return_value = None

        return {
            "media_repository": mock_media_repository,
            "storage_resolver": storage_resolver,
            "metrics_publisher": metrics_publisher,
            "event_publisher": event_publisher,
            "file_validator": file_validator,
            "storage_service": mock_storage_service,
        }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """CreateMediaCommandHandler instance wired with collaborator doubles."""

        return CreateMediaCommandHandler(
            media_repository=mock_dependencies["media_repository"],
            storage_resolver=mock_dependencies["storage_resolver"],
            metrics_publisher=mock_dependencies["metrics_publisher"],
            event_publisher=mock_dependencies["event_publisher"],
            file_validator=mock_dependencies["file_validator"],
        )

    @pytest.fixture
    def valid_video_command(self, test_data_factory):
        upload_data = test_data_factory.create_upload_data(MediaType.VIDEO)
        return CreateMediaCommand(
            user_id="user_123",
            file=upload_data["file"],
            filename=upload_data["filename"],
            storage_provider=upload_data["storage_provider"],
        )

    @pytest.fixture
    def valid_audio_command(self, test_data_factory):
        upload_data = test_data_factory.create_upload_data(MediaType.AUDIO)
        return CreateMediaCommand(
            user_id="user_123",
            file=upload_data["file"],
            filename=upload_data["filename"],
            storage_provider=upload_data["storage_provider"],
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_video_media_success(
        self,
        handler,
        mock_dependencies,
        valid_video_command,
        test_data_factory,
    ):
        """Successful flow validates, resolves storage and publishes side effects."""

        expected_media = test_data_factory.create_video_media(
            user_id=valid_video_command.user_id,
            filename=valid_video_command.filename,
        )
        mock_dependencies["media_repository"].save.return_value = expected_media
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_video_command.filename}",
            "size": len(valid_video_command.file),
        }

        result = await handler.handle(valid_video_command)

        assert result == expected_media
        mock_dependencies["file_validator"].validate.assert_called_once_with(
            valid_video_command.file, valid_video_command.filename
        )
        mock_dependencies["storage_resolver"].resolve.assert_called_once_with(
            valid_video_command.storage_provider
        )
        mock_dependencies["storage_service"].upload.assert_awaited_once()
        mock_dependencies["media_repository"].save.assert_awaited_once()
        mock_dependencies["metrics_publisher"].publish.assert_awaited_once_with(
            expected_media, len(valid_video_command.file)
        )
        mock_dependencies["event_publisher"].publish_media_uploaded.assert_awaited_once_with(
            expected_media, f"/uploads/{valid_video_command.filename}"
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_audio_media_success(
        self,
        handler,
        mock_dependencies,
        valid_audio_command,
        test_data_factory,
    ):
        """Metrics publisher receives the saved media and file size."""

        expected_media = test_data_factory.create_audio_media(
            user_id=valid_audio_command.user_id,
            filename=valid_audio_command.filename,
        )
        mock_dependencies["media_repository"].save.return_value = expected_media
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_audio_command.filename}",
            "size": len(valid_audio_command.file),
        }

        await handler.handle(valid_audio_command)

        publish_args = mock_dependencies["metrics_publisher"].publish.await_args
        assert publish_args.args[0] is expected_media
        assert publish_args.args[1] == len(valid_audio_command.file)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_invalid_file_type(self, handler, mock_dependencies):
        invalid_command = CreateMediaCommand(
            user_id="user_123",
            file=b"invalid_content",
            filename="document.exe",
            storage_provider="local",
        )

        with pytest.raises(ValidationError, match="Unsupported file type"):
            await handler.handle(invalid_command)

        mock_dependencies["storage_service"].upload.assert_not_awaited()
        mock_dependencies["media_repository"].save.assert_not_awaited()
        mock_dependencies["event_publisher"].publish_media_uploaded.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_file_validator_error(self, handler, mock_dependencies):
        mock_dependencies["file_validator"].validate.side_effect = ValidationError(
            "file", "large_video.mp4", "File size exceeds maximum limit"
        )

        command = CreateMediaCommand(
            user_id="user_123",
            file=b"too_large",
            filename="large_video.mp4",
            storage_provider="local",
        )

        with pytest.raises(ValidationError, match="File size exceeds maximum limit"):
            await handler.handle(command)

        mock_dependencies["storage_resolver"].resolve.assert_not_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_storage_failure(
        self, handler, mock_dependencies, valid_audio_command
    ):
        mock_dependencies["storage_service"].upload.side_effect = StorageError(
            "Storage service unavailable"
        )

        with pytest.raises(StorageError, match="Storage service unavailable"):
            await handler.handle(valid_audio_command)

        mock_dependencies["storage_service"].upload.assert_awaited_once()
        mock_dependencies["media_repository"].save.assert_not_awaited()
        mock_dependencies["event_publisher"].publish_media_uploaded.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_repository_failure(
        self, handler, mock_dependencies, valid_audio_command
    ):
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": "/uploads/test.mp3",
            "size": len(valid_audio_command.file),
        }
        mock_dependencies["media_repository"].save.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await handler.handle(valid_audio_command)

        mock_dependencies["storage_service"].upload.assert_awaited_once()
        mock_dependencies["media_repository"].save.assert_awaited_once()
        mock_dependencies["event_publisher"].publish_media_uploaded.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_sets_correct_metadata(
        self, handler, mock_dependencies, valid_video_command
    ):
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_video_command.filename}",
            "size": len(valid_video_command.file),
            "etag": "mock_etag_123",
        }

        saved_media: Media | None = None

        async def capture_save(media):
            nonlocal saved_media
            saved_media = media
            return media

        mock_dependencies["media_repository"].save.side_effect = capture_save

        await handler.handle(valid_video_command)

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
    async def test_create_media_event_collaboration(
        self, handler, mock_dependencies, valid_audio_command, test_data_factory
    ):
        expected_media = test_data_factory.create_audio_media(
            user_id=valid_audio_command.user_id,
            filename=valid_audio_command.filename,
        )
        mock_dependencies["media_repository"].save.return_value = expected_media
        mock_dependencies["storage_service"].upload.return_value = {
            "file_path": f"/uploads/{valid_audio_command.filename}",
            "size": len(valid_audio_command.file),
        }

        await handler.handle(valid_audio_command)

        mock_dependencies["event_publisher"].publish_media_uploaded.assert_awaited_once_with(
            expected_media, f"/uploads/{valid_audio_command.filename}"
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_different_storage_providers(
        self, handler, mock_dependencies, test_data_factory
    ):
        storage_providers = ["local", "s3", "minio"]

        for provider in storage_providers:
            command = CreateMediaCommand(
                user_id="user_123",
                file=b"test_content",
                filename=f"test_{provider}.mp3",
                storage_provider=provider,
            )

            mock_dependencies["media_repository"].save.return_value = test_data_factory.create_audio_media(
                user_id=command.user_id,
                filename=command.filename,
                storage_provider=provider,
            )
            mock_dependencies["storage_service"].upload.return_value = {
                "file_path": f"/uploads/{command.filename}",
                "size": len(command.file),
            }

            await handler.handle(command)

            mock_dependencies["storage_resolver"].resolve.assert_called_with(provider)
            mock_dependencies["storage_resolver"].resolve.reset_mock()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_mime_type_detection(
        self, handler, mock_dependencies, test_data_factory
    ):
        test_cases = [
            ("test.mp3", MediaType.AUDIO, "audio/mpeg"),
            ("test.wav", MediaType.AUDIO, "audio/wav"),
            ("test.mp4", MediaType.VIDEO, "video/mp4"),
            ("test.avi", MediaType.VIDEO, "video/x-msvideo"),
        ]

        for filename, expected_type, expected_mime in test_cases:
            command = CreateMediaCommand(
                user_id="user_123",
                file=b"test_content",
                filename=filename,
                storage_provider="local",
            )

            expected_media = test_data_factory.create_media(
                media_type=expected_type,
                filename=filename,
            )
            mock_dependencies["media_repository"].save.return_value = expected_media
            mock_dependencies["storage_service"].upload.return_value = {
                "file_path": f"/uploads/{filename}",
                "size": len(command.file),
            }

            await handler.handle(command)

            upload_call = mock_dependencies["storage_service"].upload.await_args
            assert upload_call.kwargs["content_type"] == expected_mime
            mock_dependencies["storage_service"].upload.reset_mock()
