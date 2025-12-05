"""Unit tests for TextAnalysisService."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.text_analysis.application.service import TextAnalysisService
from src.text_analysis.domain.entities import Analysis
from src.text_analysis.domain.errors import EmptyTextError
from src.text_analysis.domain.value_objects import SentimentLabel, Sentiment, Topic, TextChunk
from src.text_analysis.application.dto import AnalysisResultDTO

@pytest.fixture
def mock_ports():
    return {
        "sentiment_service": MagicMock(),
        "embedding_service": MagicMock(),
        "topic_modeling": MagicMock(),
        "text_generation": MagicMock(),
        "chunker": MagicMock(),
        "repository": MagicMock(),
        "event_bus": MagicMock(),
        "metrics": AsyncMock(),
    }

@pytest.fixture
def service(mock_ports):
    return TextAnalysisService(
        sentiment_service=mock_ports["sentiment_service"],
        embedding_service=mock_ports["embedding_service"],
        topic_modeling=mock_ports["topic_modeling"],
        text_generation=mock_ports["text_generation"],
        chunker=mock_ports["chunker"],
        repository=mock_ports["repository"],
        metrics=mock_ports["metrics"],
        event_bus=mock_ports["event_bus"],
    )

@pytest.mark.asyncio
async def test_analyze_text_content_success(service, mock_ports):
    # Arrange
    text_content = "This is a test text."
    chunks = [TextChunk(id="1", text="This is a test text.", start=0.0, end=1.0)]
    sentiments = [Sentiment(chunk_id="1", score=0.9, label=SentimentLabel.POSITIVE)]
    topics = [Topic(topic_id=1, keywords=["test"], snippets=["This is a test"], size=1)]
    
    mock_ports["chunker"].chunk.return_value = chunks
    mock_ports["sentiment_service"].analyze.return_value = sentiments
    mock_ports["embedding_service"].embed.return_value = [[0.1, 0.2]]
    mock_ports["topic_modeling"].model_topics.return_value = (topics, {})
    mock_ports["text_generation"].is_available.return_value = False
    mock_ports["repository"].save.return_value = "analysis_123"

    # Act
    result = await service.analyze_text_content(
        text_content=text_content,
        media_id="media_1",
        transcription_id="trans_1",
        user_id="user_1"
    )

    # Assert
    assert result["media_id"] == "media_1"
    assert result["transcription_id"] == "trans_1"
    assert result["user_id"] == "user_1"
    assert result["overall_sentiment"] == SentimentLabel.POSITIVE.value
    
    mock_ports["chunker"].chunk.assert_called_once()
    mock_ports["sentiment_service"].analyze.assert_called_once()
    mock_ports["repository"].save.assert_called_once()
    mock_ports["metrics"].record_operation.assert_called_once()
    
    # Verify events
    assert mock_ports["event_bus"].publish.call_count == 3  # Sentiment, Summarization, Topic

@pytest.mark.asyncio
async def test_analyze_text_content_empty_text(service):
    with pytest.raises(EmptyTextError): # Or DomainError depending on validation
        # Document.from_payload raises EmptyTextError which inherits from somewhere
        # Let's check what Document raises. It raises EmptyTextError.
        # Wait, analyze_text_content doesn't catch it, so it should bubble up.
        # But `_perform_analysis` calls `Document.from_payload`
        await service.analyze_text_content(text_content="")

@pytest.mark.asyncio
async def test_fallback_fetch_text(service, mock_ports):
    # Simulate missing text but providing queries
    mock_queries = AsyncMock()
    service.transcription_queries = mock_queries
    
    mock_transcription = MagicMock()
    mock_transcription.text = "Fetched text"
    mock_transcription.language = "en"
    mock_transcription.segments = []
    mock_transcription.id = "trans_fetched"
    
    mock_queries.get_by_media_id.return_value = mock_transcription
    
    # Setup mocks for analysis to succeed
    mock_ports["chunker"].chunk.return_value = []
    mock_ports["sentiment_service"].analyze.return_value = []
    mock_ports["embedding_service"].embed.return_value = []
    mock_ports["topic_modeling"].model_topics.return_value = ([], {})
    mock_ports["repository"].save.return_value = "analysis_123"

    result = await service.analyze_text_content(
        media_id="media_with_text",
        text_content=None
    )
    
    assert result["media_id"] == "media_with_text"
    mock_queries.get_by_media_id.assert_called_with("media_with_text")
    # Ensure analysis was performed on "Fetched text"
    # We can check chunker call
    args, _ = mock_ports["chunker"].chunk.call_args
    document = args[0]
    assert document.text == "Fetched text"
