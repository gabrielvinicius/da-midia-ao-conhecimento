# tests/integration/media_management/test_create_media_integration.py
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.media_management.application.commands.create_media_command_handler import (
    CreateMediaCommandHandler,
)
from src.media_management.application.policies import MediaAccessPolicy
from src.media_management.application.queries.media_queries import MediaQueries
from src.media_management.application.services.media_service import MediaService
from src.media_management.application.validators import MediaUploadValidator
from src.media_management.config.settings import MediaSettings
from src.media_management.domain.media import MediaType
from src.media_management.infrastructure.media_repository import MediaRepository
from src.media_management.infrastructure.orm.media_entity import MediaEntity

# This test requires a running database, managed by the fixtures in tests/integration/conftest.py
pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_media_service_upload_persists_to_db(db_session: AsyncSession):
    """Integration test to verify that MediaService persists media via the handler."""
    media_repo = MediaRepository(db=db_session)
    media_queries = MediaQueries(media_repository=media_repo)

    mock_storage_service = AsyncMock()
    mock_storage_factory = MagicMock(return_value=mock_storage_service)
    mock_event_bus = AsyncMock()
    mock_metrics_service = AsyncMock()

    handler = CreateMediaCommandHandler.with_default_components(
        media_repository=media_repo,
        storage_service_factory=mock_storage_factory,
        event_bus=mock_event_bus,
        metrics_service=mock_metrics_service,
    )

    class _StubHandler:
        async def handle(self, *_args, **_kwargs):  # pragma: no cover - test helper
            return None

    media_service = MediaService(
        media_queries=media_queries,
        create_media_handler=handler,
        delete_media_handler=_StubHandler(),
        reprocess_media_handler=_StubHandler(),
        upload_validator=MediaUploadValidator(settings=MediaSettings()),
        access_policy=MediaAccessPolicy(),
    )

    user_id = UUID(int=0)
    created_media = await media_service.upload_media(
        user_id=user_id,
        file_content=b"test_content",
        filename="test.pdf",
        storage_provider="local",
    )

    # Assert: Verify the entity was persisted correctly by querying the DB directly
    # The handler already commits, so we can query immediately.
    result = await db_session.execute(
        select(MediaEntity).where(MediaEntity.id == created_media.id)
    )
    persisted_media = result.scalar_one_or_none()

    assert persisted_media is not None
    assert persisted_media.id == created_media.id
    assert persisted_media.media_type == MediaType.TEXT
    assert persisted_media.storage_provider == "local"
    assert persisted_media is not None
    assert str(persisted_media.user_id) == str(user_id)
