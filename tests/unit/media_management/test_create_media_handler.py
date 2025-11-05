"""Unit tests for the CreateMediaCommandHandler collaboration flow."""

import mimetypes
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.media_management.application.commands.components.storage_uploader import (
    StorageUploadResult,
)
from src.media_management.application.commands.components.upload_metadata_mapper import (
    UploadMetadata,
)
from src.media_management.application.commands.create_media_command import (
    CreateMediaCommand,
)
from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.domain.media import Media, MediaStatus, MediaType
from src.shared.exceptions.domain_exceptions import StorageError, ValidationError


class TestCreateMediaCommandHandler:
    """Ensures the handler delegates work to dedicated collaborators."""

    @pytest.fixture
    def collaborators(self, mock_media_repository):
        storage_uploader = AsyncMock()
        storage_uploader.upload.return_value = StorageUploadResult(
            destination_path="media/uuid/file.ext",
            metadata={"file_path": "media/uuid/file.ext", "size": 128},
        )

        metadata_mapper = MagicMock()
        metadata_mapper.map.return_value = UploadMetadata(
            stored_path="media/uuid/file.ext",
            file_size=128,
        )

        side_effect_publisher = AsyncMock()

        file_validator = MagicMock()
        file_validator.validate.return_value = None

        return {
            "media_repository": mock_media_repository,
            "storage_uploader": storage_uploader,
            "metadata_mapper": metadata_mapper,
            "side_effect_publisher": side_effect_publisher,
            "file_validator": file_validator,
        }

    @pytest.fixture
    def handler(self, collaborators):
        return CreateMediaCommandHandler(
            media_repository=collaborators["media_repository"],
            storage_uploader=collaborators["storage_uploader"],
            metadata_mapper=collaborators["metadata_mapper"],
            side_effect_publisher=collaborators["side_effect_publisher"],
            file_validator=collaborators["file_validator"],
        )

    @pytest.fixture
    def valid_video_command(self, test_data_factory):
        upload_data = test_data_factory.create_upload_data(MediaType.VIDEO)
        return CreateMediaCommand(
            user_id=str(uuid4()),
            file=upload_data["file"],
            filename=upload_data["filename"],
            storage_provider=upload_data["storage_provider"],
        )

    @pytest.fixture
    def valid_audio_command(self, test_data_factory):
        upload_data = test_data_factory.create_upload_data(MediaType.AUDIO)
        return CreateMediaCommand(
            user_id=str(uuid4()),
            file=upload_data["file"],
            filename=upload_data["filename"],
            storage_provider=upload_data["storage_provider"],
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_video_media_success(
        self,
        handler,
        collaborators,
        valid_video_command,
        test_data_factory,
    ):
        """Successful flow validates input and triggers all collaborators."""
        expected_media = test_data_factory.create_video_media(
            user_id=valid_video_command.user_id,
            filename=valid_video_command.filename,
        )
        collaborators["media_repository"].save.return_value = expected_media

        result = await handler.handle(valid_video_command)

        assert result == expected_media
        collaborators["file_validator"].validate.assert_called_once_with(
            valid_video_command.file, valid_video_command.filename
        )
        collaborators["storage_uploader"].upload.assert_awaited_once()
        collaborators["metadata_mapper"].map.assert_called_once()
        collaborators["media_repository"].save.assert_awaited_once()
        collaborators["side_effect_publisher"].publish.assert_awaited_once_with(
            expected_media,
            collaborators["metadata_mapper"].map.return_value,
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_audio_media_success(
        self,
        handler,
        collaborators,
        valid_audio_command,
        test_data_factory,
    ):
        """Metrics publisher receives the saved media and file size."""
        expected_media = test_data_factory.create_audio_media(
            user_id=valid_audio_command.user_id,
            filename=valid_audio_command.filename,
        )
        collaborators["media_repository"].save.return_value = expected_media
        collaborators["metadata_mapper"].map.return_value = UploadMetadata(
            stored_path=f"/uploads/{valid_audio_command.filename}",
            file_size=len(valid_audio_command.file),
        )

        await handler.handle(valid_audio_command)

        publish_args = collaborators["side_effect_publisher"].publish.await_args
        assert publish_args.args[0] is expected_media
        assert publish_args.args[1].file_size == len(valid_audio_command.file)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_invalid_file_type(self, handler, collaborators):
        invalid_command = CreateMediaCommand(
            user_id="user_123",
            file=b"invalid_content",
            filename="document.exe",
            storage_provider="local",
        )

        with pytest.raises(ValidationError, match="Unsupported file type"):
            await handler.handle(invalid_command)

        collaborators["storage_uploader"].upload.assert_not_awaited()
        collaborators["media_repository"].save.assert_not_awaited()
        collaborators["side_effect_publisher"].publish.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_file_validator_error(self, handler, collaborators):
        collaborators["file_validator"].validate.side_effect = ValidationError(
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

        collaborators["storage_uploader"].upload.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_storage_failure(
        self, handler, collaborators, valid_audio_command
    ):
        collaborators["storage_uploader"].upload.side_effect = StorageError(
            operation="upload",
            reason="Storage service unavailable",
        )

        with pytest.raises(StorageError, match="Storage service unavailable"):
            await handler.handle(valid_audio_command)

        collaborators["storage_uploader"].upload.assert_awaited_once()
        collaborators["media_repository"].save.assert_not_awaited()
        collaborators["side_effect_publisher"].publish.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_repository_failure(
        self, handler, collaborators, valid_audio_command
    ):
        collaborators["metadata_mapper"].map.return_value = UploadMetadata(
            stored_path="/uploads/test.mp3",
            file_size=len(valid_audio_command.file),
        )
        collaborators["media_repository"].save.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            await handler.handle(valid_audio_command)

        collaborators["storage_uploader"].upload.assert_awaited_once()
        collaborators["media_repository"].save.assert_awaited_once()
        collaborators["side_effect_publisher"].publish.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_sets_correct_metadata(
        self, handler, collaborators, valid_video_command
    ):
        collaborators["metadata_mapper"].map.return_value = UploadMetadata(
            stored_path=f"/uploads/{valid_video_command.filename}",
            file_size=len(valid_video_command.file),
        )

        saved_media: Media | None = None

        async def capture_save(media):
            nonlocal saved_media
            saved_media = media
            return media

        collaborators["media_repository"].save.side_effect = capture_save

        await handler.handle(valid_video_command)

        assert saved_media is not None
        assert str(saved_media.user_id) == valid_video_command.user_id
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
        self, handler, collaborators, valid_audio_command, test_data_factory
    ):
        expected_media = test_data_factory.create_audio_media(
            user_id=valid_audio_command.user_id,
            filename=valid_audio_command.filename,
        )
        collaborators["media_repository"].save.return_value = expected_media
        metadata = UploadMetadata(
            stored_path=f"/uploads/{valid_audio_command.filename}",
            file_size=len(valid_audio_command.file),
        )
        collaborators["metadata_mapper"].map.return_value = metadata

        await handler.handle(valid_audio_command)

        collaborators["side_effect_publisher"].publish.assert_awaited_once_with(
            expected_media, metadata
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_different_storage_providers(
        self, handler, collaborators, test_data_factory
    ):
        storage_providers = ["local", "s3", "minio"]

        for provider in storage_providers:
            command = CreateMediaCommand(
                user_id=str(uuid4()),
                file=b"test_content",
                filename=f"test_{provider}.mp3",
                storage_provider=provider,
            )

            collaborators["media_repository"].save.return_value = test_data_factory.create_audio_media(
                user_id=command.user_id,
                filename=command.filename,
                storage_provider=provider,
            )
            collaborators["metadata_mapper"].map.return_value = UploadMetadata(
                stored_path=f"/uploads/{command.filename}",
                file_size=len(command.file),
            )

            await handler.handle(command)

            upload_call = collaborators["storage_uploader"].upload.await_args
            assert upload_call.kwargs["command"].storage_provider == provider
            collaborators["storage_uploader"].upload.reset_mock()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_media_mime_type_detection(
        self, handler, collaborators, test_data_factory
    ):
        test_cases = [
            ("test.mp3", MediaType.AUDIO),
            ("test.wav", MediaType.AUDIO),
            ("test.mp4", MediaType.VIDEO),
            ("test.avi", MediaType.VIDEO),
        ]

        for filename, expected_type in test_cases:
            command = CreateMediaCommand(
                user_id=str(uuid4()),
                file=b"test_content",
                filename=filename,
                storage_provider="local",
            )

            expected_media = test_data_factory.create_media(
                media_type=expected_type,
                filename=filename,
            )
            collaborators["media_repository"].save.return_value = expected_media
            collaborators["metadata_mapper"].map.return_value = UploadMetadata(
                stored_path=f"/uploads/{filename}",
                file_size=len(command.file),
            )

            await handler.handle(command)

            upload_call = collaborators["storage_uploader"].upload.await_args
            guessed_mime = mimetypes.guess_type(filename)[0] or "application/octet-stream"
            assert upload_call.kwargs["content_type"] == guessed_mime
            collaborators["storage_uploader"].upload.reset_mock()
