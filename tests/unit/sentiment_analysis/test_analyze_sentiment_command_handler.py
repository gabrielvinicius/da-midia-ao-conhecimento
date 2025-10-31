# tests/unit/sentiment_analysis/test_analyze_sentiment_command_handler.py
"""
Unit tests for AnalyzeSentimentCommandHandler.
Tests the CQRS command handling pattern for sentiment analysis processing with comprehensive scenarios.
Validates ML service integration, emotion detection, and event-driven architecture.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from src.sentiment_analysis.application.commands.analyze_sentiment_command import AnalyzeSentimentCommand
from src.sentiment_analysis.application.commands.analyze_sentiment_command_handler import AnalyzeSentimentCommandHandler
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.shared.events.domain_events import SentimentAnalysisCompleted
from src.shared.exceptions.domain_exceptions import ValidationError, ProcessingError


class TestAnalyzeSentimentCommandHandler:
    """Test suite for AnalyzeSentimentCommandHandler following DDD and Event-Driven patterns."""

    @pytest.fixture
    def mock_dependencies(self, mock_sentiment_analysis_service, mock_event_bus, 
                         mock_transcription_queries, mock_connection_manager, mock_metrics_service):
        """Complete set of mocked dependencies for AnalyzeSentimentCommandHandler."""
        # Create a proper mock repository
        mock_analysis_repository = AsyncMock()
        mock_analysis_repository.save = AsyncMock()
        mock_analysis_repository.find_by_transcription_id = AsyncMock()
        mock_analysis_repository.find_by_id = AsyncMock()
        
        return {
            "sentiment_service": mock_sentiment_analysis_service,
            "analysis_repository": mock_analysis_repository,
            "transcription_queries": mock_transcription_queries,
            "event_bus": mock_event_bus,
            "connection_manager": mock_connection_manager,
            "metrics_service": mock_metrics_service
        }

    @pytest.fixture
    def handler(self, mock_dependencies):
        """AnalyzeSentimentCommandHandler instance with mocked dependencies."""
        return AnalyzeSentimentCommandHandler(**mock_dependencies)

    @pytest.fixture
    def valid_command(self, test_data_factory):
        """Valid AnalyzeSentimentCommand for testing."""
        return AnalyzeSentimentCommand(
            transcription_id="transcription_123",
            provider="transformers",
            model="distilbert-base-uncased"
        )

    @pytest.fixture
    def sample_transcription(self, test_data_factory):
        """Sample transcription entity for testing."""
        return test_data_factory.create_transcription(
            id="transcription_123",
            text="I am very happy with this amazing product! It works perfectly and exceeded my expectations. However, the delivery was quite slow and frustrating. Overall, I would recommend it to others.",
            status=TranscriptionStatus.COMPLETED
        )

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_successful_sentiment_analysis_mixed_emotions(self, handler, mock_dependencies, 
                                                              valid_command, sample_transcription, test_data_factory):
        """Test successful sentiment analysis with mixed positive and negative emotions."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        
        mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
            "overall_sentiment": "positive",
            "sentiment_score": 0.3,  # Slightly positive due to mixed content
            "confidence": 0.78,
            "emotions": {
                "joy": 0.65,
                "satisfaction": 0.72,
                "frustration": 0.45,
                "disappointment": 0.32
            },
            "sentence_sentiments": [
                {"text": "I am very happy with this amazing product!", "sentiment": "positive", "score": 0.89},
                {"text": "It works perfectly and exceeded my expectations.", "sentiment": "positive", "score": 0.85},
                {"text": "However, the delivery was quite slow and frustrating.", "sentiment": "negative", "score": -0.67},
                {"text": "Overall, I would recommend it to others.", "sentiment": "positive", "score": 0.71}
            ],
            "processing_time": 2.8
        }
        
        created_analysis = test_data_factory.create_sentiment_analysis(
            transcription_id=valid_command.transcription_id
        )
        mock_dependencies["analysis_repository"].save.return_value = created_analysis

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.overall_sentiment == "positive"
        assert result.sentiment_score == 0.3
        assert result.confidence == 0.78
        assert "joy" in result.emotions
        assert "frustration" in result.emotions
        assert len(result.sentence_sentiments) == 4
        
        # Verify service was called with correct parameters
        mock_dependencies["sentiment_service"].analyze_sentiment.assert_awaited_once()
        analyze_call = mock_dependencies["sentiment_service"].analyze_sentiment.await_args
        assert sample_transcription.text in str(analyze_call)
        
        # Verify repository save and event publishing
        mock_dependencies["analysis_repository"].save.assert_awaited_once()
        mock_dependencies["event_bus"].publish.assert_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_purely_positive(self, handler, mock_dependencies, 
                                                    valid_command, test_data_factory):
        """Test sentiment analysis for purely positive content."""
        # Arrange
        positive_transcription = test_data_factory.create_transcription(
            id="transcription_123",
            text="This is absolutely wonderful! I love everything about it. Amazing experience, highly recommended!",
            status=TranscriptionStatus.COMPLETED
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = positive_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        
        mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
            "overall_sentiment": "positive",
            "sentiment_score": 0.92,
            "confidence": 0.95,
            "emotions": {
                "joy": 0.88,
                "excitement": 0.79,
                "satisfaction": 0.91,
                "love": 0.84
            },
            "sentence_sentiments": [
                {"text": "This is absolutely wonderful!", "sentiment": "positive", "score": 0.94},
                {"text": "I love everything about it.", "sentiment": "positive", "score": 0.89},
                {"text": "Amazing experience, highly recommended!", "sentiment": "positive", "score": 0.93}
            ],
            "processing_time": 1.5
        }
        
        created_analysis = test_data_factory.create_sentiment_analysis(
            transcription_id=valid_command.transcription_id,
            overall_sentiment="positive",
            sentiment_score=0.92
        )
        mock_dependencies["analysis_repository"].save.return_value = created_analysis

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.overall_sentiment == "positive"
        assert result.sentiment_score > 0.9
        assert result.confidence > 0.9
        assert all(emotion_score > 0.7 for emotion_score in result.emotions.values())

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_purely_negative(self, handler, mock_dependencies, 
                                                    valid_command, test_data_factory):
        """Test sentiment analysis for purely negative content."""
        # Arrange
        negative_transcription = test_data_factory.create_transcription(
            id="transcription_123",
            text="This is terrible! I hate everything about this product. Worst experience ever, completely disappointed.",
            status=TranscriptionStatus.COMPLETED
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = negative_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        
        mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
            "overall_sentiment": "negative",
            "sentiment_score": -0.87,
            "confidence": 0.91,
            "emotions": {
                "anger": 0.82,
                "disappointment": 0.89,
                "frustration": 0.76,
                "disgust": 0.73
            },
            "sentence_sentiments": [
                {"text": "This is terrible!", "sentiment": "negative", "score": -0.91},
                {"text": "I hate everything about this product.", "sentiment": "negative", "score": -0.85},
                {"text": "Worst experience ever, completely disappointed.", "sentiment": "negative", "score": -0.86}
            ],
            "processing_time": 1.8
        }
        
        created_analysis = test_data_factory.create_sentiment_analysis(
            transcription_id=valid_command.transcription_id,
            overall_sentiment="negative",
            sentiment_score=-0.87
        )
        mock_dependencies["analysis_repository"].save.return_value = created_analysis

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.overall_sentiment == "negative"
        assert result.sentiment_score < -0.8
        assert "anger" in result.emotions
        assert "disappointment" in result.emotions

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_neutral_content(self, handler, mock_dependencies, 
                                                    valid_command, test_data_factory):
        """Test sentiment analysis for neutral content."""
        # Arrange
        neutral_transcription = test_data_factory.create_transcription(
            id="transcription_123",
            text="The weather is sunny today. We have a meeting at 3 PM. Please review the quarterly report.",
            status=TranscriptionStatus.COMPLETED
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = neutral_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        
        mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.05,
            "confidence": 0.82,
            "emotions": {
                "neutral": 0.85,
                "calm": 0.72
            },
            "sentence_sentiments": [
                {"text": "The weather is sunny today.", "sentiment": "neutral", "score": 0.12},
                {"text": "We have a meeting at 3 PM.", "sentiment": "neutral", "score": -0.02},
                {"text": "Please review the quarterly report.", "sentiment": "neutral", "score": 0.01}
            ],
            "processing_time": 1.2
        }
        
        created_analysis = test_data_factory.create_sentiment_analysis(
            transcription_id=valid_command.transcription_id,
            overall_sentiment="neutral",
            sentiment_score=0.05
        )
        mock_dependencies["analysis_repository"].save.return_value = created_analysis

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.overall_sentiment == "neutral"
        assert -0.1 <= result.sentiment_score <= 0.1
        assert "neutral" in result.emotions

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_already_exists(self, handler, mock_dependencies, 
                                                   valid_command, sample_transcription, test_data_factory):
        """Test that existing sentiment analysis is returned without reprocessing."""
        # Arrange
        existing_analysis = test_data_factory.create_sentiment_analysis(
            transcription_id=valid_command.transcription_id,
            overall_sentiment="positive",
            sentiment_score=0.75
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = existing_analysis

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result == existing_analysis
        assert result.sentiment_score == 0.75
        
        # Verify that sentiment service was not called
        mock_dependencies["sentiment_service"].analyze_sentiment.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_transcription_not_found(self, handler, mock_dependencies, valid_command):
        """Test error handling when transcription is not found."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = None

        # Act & Assert
        with pytest.raises(ValidationError, match="Transcription not found"):
            await handler.handle(valid_command)
        
        mock_dependencies["sentiment_service"].analyze_sentiment.assert_not_awaited()
        mock_dependencies["analysis_repository"].save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_transcription_not_completed(self, handler, mock_dependencies, 
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
    async def test_sentiment_analysis_text_too_short(self, handler, mock_dependencies, 
                                                   valid_command, test_data_factory):
        """Test error handling for transcription text that is too short for analysis."""
        # Arrange
        short_transcription = test_data_factory.create_transcription(
            id=valid_command.transcription_id,
            text="Ok.",  # Very short text
            status=TranscriptionStatus.COMPLETED
        )
        mock_dependencies["transcription_queries"].get_by_id.return_value = short_transcription

        # Act & Assert
        with pytest.raises(ValidationError, match="Text too short for sentiment analysis"):
            await handler.handle(valid_command)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_service_failure(self, handler, mock_dependencies, 
                                                    valid_command, sample_transcription):
        """Test error handling when sentiment analysis service fails."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        mock_dependencies["sentiment_service"].analyze_sentiment.side_effect = Exception("ML service error")

        # Act & Assert
        with pytest.raises(ProcessingError, match="Sentiment analysis failed"):
            await handler.handle(valid_command)
        
        # Verify that error was properly handled
        mock_dependencies["analysis_repository"].save.assert_not_awaited()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_with_real_time_progress(self, handler, mock_dependencies, 
                                                            valid_command, sample_transcription, test_data_factory):
        """Test sentiment analysis with real-time progress updates via WebSocket."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        
        mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
            "overall_sentiment": "positive",
            "sentiment_score": 0.65,
            "confidence": 0.83,
            "emotions": {"joy": 0.7, "satisfaction": 0.65},
            "sentence_sentiments": [],
            "processing_time": 3.1
        }
        
        created_analysis = test_data_factory.create_sentiment_analysis(
            transcription_id=valid_command.transcription_id
        )
        mock_dependencies["analysis_repository"].save.return_value = created_analysis

        # Act
        result = await handler.handle(valid_command)

        # Assert
        assert result.sentiment_score == 0.65
        
        # Verify WebSocket progress updates were sent
        mock_dependencies["connection_manager"].send_personal_message.assert_called()

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_events_publishing(self, handler, mock_dependencies, 
                                                      valid_command, sample_transcription, test_data_factory):
        """Test that appropriate domain events are published during sentiment analysis."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
            "overall_sentiment": "neutral",
            "sentiment_score": 0.1,
            "confidence": 0.75,
            "emotions": {"neutral": 0.8},
            "sentence_sentiments": [],
            "processing_time": 2.0
        }
        
        created_analysis = test_data_factory.create_sentiment_analysis(transcription_id=valid_command.transcription_id)
        mock_dependencies["analysis_repository"].save.return_value = created_analysis

        # Act
        await handler.handle(valid_command)

        # Assert
        # Should publish SentimentAnalysisCompleted event
        mock_dependencies["event_bus"].publish.assert_awaited()
        published_event = mock_dependencies["event_bus"].publish.await_args.args[0]
        assert isinstance(published_event, SentimentAnalysisCompleted)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_multiple_models(self, handler, mock_dependencies, 
                                                     sample_transcription, test_data_factory):
        """Test sentiment analysis with different ML models."""
        models = ["distilbert-base-uncased", "roberta-base", "bert-base-uncased"]
        
        for model in models:
            # Arrange
            command = AnalyzeSentimentCommand(
                transcription_id=f"transcription_{model}",
                provider="transformers",
                model=model
            )
            
            mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
            mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
            mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
                "overall_sentiment": "positive",
                "sentiment_score": 0.7,
                "confidence": 0.85,
                "emotions": {"satisfaction": 0.75},
                "sentence_sentiments": [],
                "processing_time": 2.5
            }
            
            created_analysis = test_data_factory.create_sentiment_analysis(
                transcription_id=command.transcription_id,
                model=model
            )
            mock_dependencies["analysis_repository"].save.return_value = created_analysis

            # Act
            result = await handler.handle(command)

            # Assert
            assert result.model == model

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_sentiment_analysis_metrics_recording(self, handler, mock_dependencies, 
                                                      valid_command, sample_transcription, test_data_factory):
        """Test that performance metrics are properly recorded."""
        # Arrange
        mock_dependencies["transcription_queries"].get_by_id.return_value = sample_transcription
        mock_dependencies["analysis_repository"].find_by_transcription_id.return_value = None
        mock_dependencies["sentiment_service"].analyze_sentiment.return_value = {
            "overall_sentiment": "positive",
            "sentiment_score": 0.8,
            "confidence": 0.9,
            "emotions": {"joy": 0.85},
            "sentence_sentiments": [],
            "processing_time": 4.2
        }
        
        created_analysis = test_data_factory.create_sentiment_analysis(
            transcription_id=valid_command.transcription_id,
            processing_time=4.2
        )
        mock_dependencies["analysis_repository"].save.return_value = created_analysis

        # Act
        await handler.handle(valid_command)

        # Assert
        # Verify metrics were recorded
        mock_dependencies["metrics_service"].increment_counter.assert_called()
        mock_dependencies["metrics_service"].record_histogram.assert_called()
        
        # Check specific metrics calls
        counter_calls = [call.args[0] for call in mock_dependencies["metrics_service"].increment_counter.call_args_list]
        assert "sentiment_analysis.started" in counter_calls
        assert "sentiment_analysis.completed" in counter_calls