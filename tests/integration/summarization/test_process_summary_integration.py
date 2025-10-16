# tests/integration/summarization/test_process_summary_integration.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from src.media_management.domain.media import Media, MediaType
from src.media_management.infrastructure.media_repository import MediaRepository
from src.summarization.domain.summary import Summary, SummaryStatus
from src.summarization.infrastructure.summary_repository import SummaryRepository
from src.summarization.application.commands.process_summary_command import ProcessSummaryCommand
from src.summarization.application.commands.process_summary_command_handler import ProcessSummaryCommandHandler

pytestmark = pytest.mark.integration

@pytest.mark.asyncio
async def test_process_summary_handler_persists_summary(db_session: AsyncSession):
    """
    Integration test to verify that the ProcessSummaryCommandHandler correctly
    creates a Summary record in the database.
    """
    # Arrange: Create a media item in the DB to associate the summary with
    media_repo = MediaRepository(db=db_session)
    media_id = uuid4()
    user_id = uuid4()
    initial_media = Media(
        id=media_id,
        user_id=user_id,
        original_file_path="test/path.txt",
        media_type=MediaType.TEXT,
        storage_provider="local"
    )
    await media_repo.save(initial_media)

    # Arrange: Create real repository and mock external services
    summary_repo = SummaryRepository(db=db_session)
    
    mock_summarizer = AsyncMock()
    mock_summarizer.summarize.return_value = "This is the final summary."
    mock_summarizer.provider_name = "mock_summarizer"

    handler = ProcessSummaryCommandHandler(
        summarizer=mock_summarizer,
        summary_repo=summary_repo,
        metrics_service=AsyncMock(),
        analytics_queries=AsyncMock(),
        event_bus=AsyncMock()
    )

    command = ProcessSummaryCommand(
        media_id=str(media_id),
        text_content="This is a very long piece of text that needs to be summarized.",
        provider="huggingface"
    )

    # Act: Execute the handler
    await handler.handle(command)

    # Assert: Verify the database state directly
    result = await db_session.execute(
        select(Summary).where(Summary.media_id == media_id)
    )
    persisted_summary = result.scalar_one_or_none()

    assert persisted_summary is not None
    assert persisted_summary.text == "This is the final summary."
    assert persisted_summary.status == SummaryStatus.COMPLETED
    assert persisted_summary.provider == "huggingface"
