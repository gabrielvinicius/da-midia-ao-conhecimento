# tests/unit/summarization/test_process_summary_handler.py
"""
Unit tests for ProcessSummaryCommandHandler.
Tests the CQRS command handling pattern for summarization processing with comprehensive scenarios.
Validates ML service integration, multiple strategies, and event-driven architecture.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime
from uuid import UUID

from src.summarization.application.commands.process_summary_command import ProcessSummaryCommand
from src.summarization.application.commands.process_summary_command_handler import ProcessSummaryCommandHandler
from src.summarization.domain.summary import Summary, SummaryStatus
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.shared.events.domain_events import SummarizationRequested, SummaryCompleted, SummarizationProgress
from src.shared.exceptions.domain_exceptions import ValidationError, ProcessingError


class TestProcessSummaryCommandHandler:
    """Test suite for ProcessSummaryCommandHandler following DDD and Event-Driven patterns."""

    @pytest.fixture
    def mock_dependencies(self, mock_summary_repository, mock_summarization_service, mock_event_bus,
                         mock_transcription_queries, mock_connection_manager, mock_metrics_service):
        """Complete set of mocked dependencies for ProcessSummaryCommandHandler."""
        return {
            "summarizer": mock_summarization_service,
            "summary_repo": mock_summary_repository,
            "transcription_queries": mock_transcription_queries,
            "metrics_service": mock_metrics_service,
            "event_bus": mock_event_bus,
            "connection_manager": mock_connection_manager
        }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """ProcessSummaryCommandHandler instance with mocked dependencies."""
        return ProcessSummaryCommandHandler(**mock_dependencies)

    @pytest.fixture
    def valid_command(self, test_data_factory):
        """Valid ProcessSummaryCommand for testing."""
        return ProcessSummaryCommand(
            transcription_id="transcription_123",
            provider="huggingface",
            strategy="extractive",
            max_length=150
        )

    @pytest.fixture
    def sample_transcription(self, test_data_factory):
        """Sample transcription entity for testing."""
        return test_data_factory.create_transcription(
            id="transcription_123",
            text="This is a comprehensive transcription text that contains multiple sentences and paragraphs discussing various topics related to technology, innovation, and software development. The content is detailed enough to provide meaningful insights when summarized through machine learning algorithms.",
            status=TranscriptionStatus.COMPLETED
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_extractive_summarization(self, handler, mock_dependencies, 
                                                     valid_command, sample_transcription, test_data_factory):
        """Test successful extractive summarization with proper event publishing."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
        
        expected_summary_text = "This is a comprehensive summary of the key technology and innovation topics."
        mock_dependencies["summarizer"].summarize.return_value = {
            "text": expected_summary_text,
            "strategy": "extractive",
            "bullet_points": [
                "Key insight about technology trends",
                "Important development in software",
                "Notable innovation breakthrough"
            ],
            "key_topics": ["technology", "innovation", "software"],
            "confidence_score": 0.87,
            "processing_time": 4.2
        }
        
        created_summary = test_data_factory.create_summary(
            transcription_id=valid_command.transcription_id,
            text_content=expected_summary_text
        )
        mock_dependencies["summary_repo"].save.return_value = created_summary

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.text == expected_summary_text
        assert result.status == SummaryStatus.COMPLETED
        assert result.provider == "huggingface"
        assert len(result.bullet_points) == 3
        assert "technology" in result.key_topics
        
        # Verify summarization service was called correctly
        mock_dependencies["summarizer"].summarize.assert_awaited_once()
        summarize_call = mock_dependencies["summarizer"].summarize.await_args
        assert sample_transcription.text in str(summarize_call)
        
        # Verify repository save and event publishing
        mock_dependencies["summary_repo"].save.assert_awaited_once()
        mock_dependencies["event_bus"].publish.assert_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summary_already_exists_completed(self, handler, mock_dependencies, 
                                                  valid_command, sample_transcription, test_data_factory):
        """Test that existing completed summary is returned without reprocessing."""
        # Arrange
        existing_summary = test_data_factory.create_summary(
            transcription_id=valid_command.transcription_id,
            text_content="Existing completed summary text",
            status=SummaryStatus.COMPLETED
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = existing_summary

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result == existing_summary
        assert result.text == "Existing completed summary text"
        assert result.status == SummaryStatus.COMPLETED
        
        # Verify that summarization service was not called
        mock_dependencies["summarizer"].summarize.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_transcription_not_found(self, handler, mock_dependencies, valid_command):
        """Test error handling when transcription is not found."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValidationError, match="Transcription not found"):
            await handler.handle(valid_command)
        
        mock_dependencies["summarizer"].summarize.assert_not_awaited()
        mock_dependencies["summary_repo"].save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_transcription_not_completed(self, handler, mock_dependencies, 
                                                           valid_command, test_data_factory):
        """Test error handling for transcription that is not completed."""
        # Arrange
        incomplete_transcription = test_data_factory.create_transcription(
            id=valid_command.transcription_id,
            status=TranscriptionStatus.PROCESSING
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = incomplete_transcription

        # Act & Assert
        with pytest.raises(ValidationError, match="Transcription not completed"):
            await handler.handle(valid_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_text_too_short(self, handler, mock_dependencies,
                                              valid_command, test_data_factory):
        """Test error handling for transcription text that is too short to summarize."""
        # Arrange
        short_transcription = test_data_factory.create_transcription(
            id=valid_command.transcription_id,
            text="Too short.",  # Very short text
            status=TranscriptionStatus.COMPLETED
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = short_transcription

        # Act & Assert
        with pytest.raises(ValidationError, match="Text too short for summarization"):
            await handler.handle(valid_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_service_failure(self, handler, mock_dependencies, 
                                               valid_command, sample_transcription):
        """Test error handling when summarization service fails."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
        mock_dependencies["summarizer"].summarize.side_effect = Exception("ML service error")

        # Act & Assert
        with pytest.raises(ProcessingError, match="Summarization failed"):
            await handler.handle(valid_command)

        # Verify that error was properly handled
        mock_dependencies["summary_repo"].save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_creates_summary_with_generated_media_id(
        self,
        handler,
        mock_dependencies,
    ):
        """Summaries without a provided media ID should receive one automatically."""

        command = ProcessSummaryCommand(
            transcription_id=None,
            provider="huggingface",
            text_content="This is a sufficiently long transcription text for summarization.",
        )

        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
        mock_dependencies["summary_repo"].add = AsyncMock()
        mock_dependencies["summary_repo"].save = AsyncMock(side_effect=lambda summary: summary)

        mock_dependencies["summarizer"].summarize.return_value = {
            "text": "Generated summary text",
        }

        result = await handler.handle(command)

        mock_dependencies["summary_repo"].add.assert_awaited_once()
        mock_dependencies["summary_repo"].save.assert_awaited_once()
        saved_summary = mock_dependencies["summary_repo"].save.await_args.args[0]

        assert isinstance(saved_summary.media_id, UUID)
        assert isinstance(result.media_id, UUID)
        assert result.text == "Generated summary text"

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_with_real_time_progress(self, handler, mock_dependencies, 
                                                       valid_command, sample_transcription, test_data_factory):
        """Test summarization with real-time progress updates via WebSocket."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
        
        mock_dependencies["summarizer"].summarize.return_value = {
            "text": "Progressive summary result",
            "strategy": "extractive",
            "bullet_points": ["Point 1", "Point 2"],
            "key_topics": ["topic1", "topic2"],
            "confidence_score": 0.88,
            "processing_time": 4.5
        }
        
        created_summary = test_data_factory.create_summary(
            transcription_id=valid_command.transcription_id,
            text_content="Progressive summary result"
        )
        mock_dependencies["summary_repo"].save.return_value = created_summary

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.text == "Progressive summary result"
        
        # Verify WebSocket progress updates were sent
        mock_dependencies["connection_manager"].send_personal_message.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_events_publishing(self, handler, mock_dependencies, 
                                                 valid_command, sample_transcription, test_data_factory):
        """Test that appropriate domain events are published during summarization."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
        mock_dependencies["summarizer"].summarize.return_value = {
            "text": "Event test summary",
            "strategy": "extractive",
            "bullet_points": [],
            "key_topics": [],
            "confidence_score": 0.75,
            "processing_time": 2.1
        }
        
        created_summary = test_data_factory.create_summary(transcription_id=valid_command.transcription_id)
        mock_dependencies["summary_repo"].save.return_value = created_summary

        # Act
        await handler.handle(valid_command)

        # Assert
        # Should publish SummarizationProgress events
        assert mock_dependencies["event_bus"].publish.call_count >= 1
        
        published_events = [call.args[0] for call in mock_dependencies["event_bus"].publish.call_args_list]
        event_types = [type(event) for event in published_events]
        
        assert SummarizationProgress in event_types

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_multiple_providers(self, handler, mock_dependencies, 
                                                   sample_transcription, test_data_factory):
        """Test summarization with different ML providers."""
        providers = ["huggingface", "openai", "anthropic"]
        
        for provider in providers:
            # Arrange
            command = ProcessSummaryCommand(
                transcription_id=f"transcription_{provider}",
                provider=provider,
                strategy="extractive"
            )
            
            mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
            mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
            mock_dependencies["summarizer"].summarize.return_value = {
                "text": f"Summary generated by {provider}",
                "strategy": "extractive",
                "bullet_points": [f"Point from {provider}"],
                "key_topics": ["provider", "testing"],
                "confidence_score": 0.80,
                "processing_time": 3.0
            }
            
            created_summary = test_data_factory.create_summary(
                transcription_id=command.transcription_id,
                text_content=f"Summary generated by {provider}"
            )
            mock_dependencies["summary_repo"].save.return_value = created_summary

            # Act
            result = await handler.handle(command)

            # Assert
            assert result.provider == provider
            assert provider in result.text

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_abstractive_strategy(self, handler, mock_dependencies, 
                                                    sample_transcription, test_data_factory):
        """Test abstractive summarization strategy."""
        # Arrange
        abstractive_command = ProcessSummaryCommand(
            transcription_id="transcription_123",
            provider="openai",
            strategy="abstractive",
            max_length=200
        )
        
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
        
        mock_dependencies["summarizer"].summarize.return_value = {
            "text": "AI-generated paraphrased summary with completely new phrasing.",
            "strategy": "abstractive",
            "bullet_points": ["Paraphrased insight", "Restructured concept"],
            "key_topics": ["AI", "paraphrasing", "generation"],
            "confidence_score": 0.82,
            "processing_time": 7.3
        }
        
        created_summary = test_data_factory.create_summary(
            transcription_id=abstractive_command.transcription_id,
            text_content="AI-generated paraphrased summary with completely new phrasing."
        )
        mock_dependencies["summary_repo"].save.return_value = created_summary

        # Act
        result = await handler.handle(abstractive_command)

        # Assert
        assert result.strategy == "abstractive"
        assert "paraphrased" in result.text.lower()
        assert result.processing_time == 7.3

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_summarization_metrics_recording(self, handler, mock_dependencies,
                                                 valid_command, sample_transcription, test_data_factory):
        """Test that performance metrics are properly recorded."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["summary_repo"].find_by_transcription_id.return_value = None
        mock_dependencies["summarizer"].summarize.return_value = {
            "text": "Metrics test summary",
            "strategy": "extractive",
            "bullet_points": [],
            "key_topics": [],
            "confidence_score": 0.82,
            "processing_time": 6.7
        }

        created_summary = test_data_factory.create_summary(
            transcription_id=valid_command.transcription_id,
            processing_time=6.7
        )
        mock_dependencies["summary_repo"].save.return_value = created_summary

        # Act
        await handler.handle(valid_command)

        # Assert
        # Verify metrics were recorded
        mock_dependencies["metrics_service"].increment_counter.assert_called()
        mock_dependencies["metrics_service"].record_histogram.assert_called()

        # Check specific metrics calls
        counter_calls = [call.args[0] for call in mock_dependencies["metrics_service"].increment_counter.call_args_list]
        assert "summarization.started" in counter_calls
        assert "summarization.completed" in counter_calls

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_persist_summary_merges_optional_fields(
        self,
        handler,
        mock_dependencies,
        test_data_factory,
    ):
        """Persisting summaries should merge supplemental fields immutably."""

        existing_summary = test_data_factory.create_summary(
            text_content="Existing summary",
            strategy="initial",
            bullet_points=("old",),
            key_topics=("old-topic",),
            confidence_score=0.5,
            processing_time=2.5,
        )

        handler._summary_repo.update = AsyncMock()
        handler._summary_repo.save = AsyncMock(side_effect=lambda summary: summary)

        summary_payload = {
            "text": "Updated summary text",
            "strategy": "updated-strategy",
            "bullet_points": ["point one", "point two"],
            "key_topics": ["topic a", "topic b"],
            "confidence_score": 0.91,
            "processing_time": 4.8,
        }

        result = await handler._persist_summary(
            media_id=str(existing_summary.media_id),
            provider="huggingface",
            summary_payload=summary_payload,
            existing=existing_summary,
        )

        assert result.text == "Updated summary text"
        assert result.strategy == "updated-strategy"
        assert result.bullet_points == tuple(summary_payload["bullet_points"])
        assert result.key_topics == tuple(summary_payload["key_topics"])
        assert result.confidence_score == 0.91
        assert result.processing_time == 4.8
        assert result.status == SummaryStatus.COMPLETED

        handler._summary_repo.update.assert_awaited_once_with(result)
        handler._summary_repo.save.assert_awaited_once_with(result)
