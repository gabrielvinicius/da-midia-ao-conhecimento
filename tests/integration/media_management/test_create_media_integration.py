# tests/integration/media_management/test_create_media_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.media_management.application.commands.create_media_command import CreateMediaCommand
from src.media_management.application.commands.create_media_command_handler import CreateMediaCommandHandler
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.domain.media import Media, MediaType


@pytest.mark.asyncio
async def test_create_media_handler_persists_to_db(db_session: AsyncSession):
    """
    Integration test to verify that the CreateMediaCommandHandler correctly
    persists a new Media entity to the database.
    """
    # Arrange: Create real repository with the test DB session, and mock external services
    media_repo = MediaRepository(db=db_session)
    mock_storage_service = AsyncMock()
    mock_storage_factory = MagicMock(return_value=mock_storage_service)
    mock_event_bus = AsyncMock()
    mock_metrics_service = AsyncMock()

    handler = CreateMediaCommandHandler(
        media_repository=media_repo,
        storage_service_factory=mock_storage_factory,
        event_bus=mock_event_bus,
        metrics_service=mock_metrics_service
    )

    command = CreateMediaCommand(
        user_id="a1b2c3d4-e5f6-7890-1234-567890abcdef",
        file=b"test_content",
        filename="test.pdf",
        storage_provider="local"
    )

    # Act: Execute the handler
    created_media = await handler.handle(command)

    # Assert: Verify the entity was persisted correctly by querying the DB directly
    # The handler already commits, so we can query immediately.
    result = await db_session.execute(
        select(Media).where(Media.id == created_gmedia.id)
    )
    persisted_media = result.scalar_one_or_none()

    assert persisted_media is not None
    assert persisted_media.id == created_media.id
    assert persisted_media.media_type == MediaType.TEXT
    assert persisted_media.storage_provider == "local"
    assert persisted_media.user_id == command.user_id
