# tests/unit/summarization/test_request_summary_command_handler.py
import pytest
from unittest.mock import AsyncMock

from src.shared.events.domain_events import SummarizationRequested
from src.summarization.application.commands.request_summary_command import RequestSummaryCommand
from src.summarization.application.commands.request_summary_command_handler import RequestSummaryCommandHandler


@pytest.fixture
def mock_event_bus():
    return AsyncMock()


@pytest.mark.asyncio
async def test_request_summary_handler_publishes_event(mock_event_bus):
    """Tests that the RequestSummaryCommandHandler correctly publishes a SummarizationRequested event."""
    # Arrange
    handler = RequestSummaryCommandHandler(event_bus=mock_event_bus)
    transcription_id = "trans1"
    provider = "huggingface"
    command = RequestSummaryCommand(transcription_id=transcription_id, provider=provider)

    # Act
    await handler.handle(command)

    # Assert
    mock_event_bus.publish.assert_awaited_once()
    published_event = mock_event_bus.publish.await_args.args[0]
    assert isinstance(published_event, SummarizationRequested)
    assert published_event.transcription_id == transcription_id
    assert published_event.provider == provider
