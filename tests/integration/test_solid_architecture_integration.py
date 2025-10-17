"""
Integration Tests for SOLID Architecture
Tests the complete SOLID refactored services working together.
"""
import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

# SOLID services to test
from src.summarization.application.services.summarization_service import SummarizationService
from src.summarization.application.services.summary_validator import SummaryValidator
from src.summarization.application.services.summary_metrics_service import SummaryMetricsService
from src.summarization.application.services.summary_state_manager_impl import SummaryStateManagerImpl

from src.transcription.application.services.speech_recognition_service import SpeechRecognitionService
from src.transcription.application.services.transcription_validator import TranscriptionValidator
from src.transcription.application.services.transcription_metrics_service_impl import TranscriptionMetricsServiceImpl
from src.transcription.application.services.transcription_state_manager_impl import TranscriptionStateManagerImpl

from src.auth.application.services.authentication_service import EnhancedAuthenticationService
from src.auth.application.services.authentication_validator import AuthenticationValidator
from src.auth.application.services.authentication_metrics_service import AuthenticationMetricsService

from src.analytics.application.services.enhanced_analytics_service import EnhancedAnalyticsService
from src.analytics.application.services.analytics_validator import AnalyticsValidator
from src.analytics.application.services.analytics_aggregator import AnalyticsAggregator

# Test fixtures
from tests.mocks.in_memory_storage import InMemoryStorage
from tests.mocks.in_memory_event_bus import InMemoryEventBus


class TestSOLIDArchitectureIntegration:
    """Integration tests for SOLID architecture services."""
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector."""
        mock = MagicMock()
        mock.record_counter = MagicMock()
        mock.record_histogram = MagicMock()
        mock.record_gauge = MagicMock()
        return mock
    
    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        mock = AsyncMock()
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_summarizer_provider(self):
        """Mock summarizer provider."""
        mock = AsyncMock()
        mock.provider_name = "test_provider"
        mock.summarize = AsyncMock(return_value="This is a test summary of the provided text.")
        return mock
    
    @pytest.fixture
    def mock_speech_recognition_provider(self):
        """Mock speech recognition provider."""
        mock = AsyncMock()
        mock.provider_name = "test_speech_provider"
        mock.transcribe = AsyncMock(return_value="This is transcribed audio content.")
        return mock
    
    @pytest.fixture
    def summarization_service(self, mock_metrics_collector, mock_cache_service, mock_summarizer_provider):
        """Create integrated summarization service."""
        validator = SummaryValidator(min_text_length=10, max_text_length=1000)
        metrics_service = SummaryMetricsService(mock_metrics_collector)
        state_manager = SummaryStateManagerImpl(mock_cache_service)
        
        return SummarizationService(
            summarizer_provider=mock_summarizer_provider,
            validator=validator,
            metrics_service=metrics_service,
            state_manager=state_manager
        )
    
    @pytest.fixture
    def transcription_service(self, mock_metrics_collector, mock_cache_service, mock_speech_recognition_provider):
        """Create integrated transcription service."""
        validator = TranscriptionValidator(
            min_audio_size=100,
            max_audio_size=1000000,
            supported_languages={"en", "es", "fr"}
        )
        metrics_service = TranscriptionMetricsServiceImpl(mock_metrics_collector)
        state_manager = TranscriptionStateManagerImpl(mock_cache_service)
        
        return SpeechRecognitionService(
            speech_recognition_provider=mock_speech_recognition_provider,
            validator=validator,
            metrics_service=metrics_service,
            state_manager=state_manager
        )
    
    @pytest.mark.asyncio
    async def test_summarization_service_integration(self, summarization_service, mock_cache_service, mock_metrics_collector):
        """Test complete summarization workflow with SOLID services."""
        # Arrange
        test_text = "This is a long text that needs to be summarized for testing purposes. " * 5
        summary_id = uuid4()
        
        # Act
        result = await summarization_service.summarize(
            text_content=test_text,
            summary_id=summary_id,
            options={"max_length": 100}
        )
        
        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify state management was called
        mock_cache_service.set.assert_called()
        
        # Verify metrics were recorded
        assert mock_metrics_collector.record_counter.called
        
        # Verify state updates
        state_calls = [call for call in mock_cache_service.set.call_args_list]
        assert len(state_calls) >= 2  # processing and completed states
    
    @pytest.mark.asyncio
    async def test_transcription_service_integration(self, transcription_service, mock_cache_service, mock_metrics_collector):
        """Test complete transcription workflow with SOLID services."""
        # Arrange
        audio_data = b"fake_audio_data" * 100  # Ensure minimum size
        transcription_id = uuid4()
        
        # Act
        result = await transcription_service.transcribe(
            audio_bytes=audio_data,
            language="en",
            transcription_id=transcription_id,
            options={"format": "mp3"}
        )
        
        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify state management
        mock_cache_service.set.assert_called()
        
        # Verify metrics
        assert mock_metrics_collector.record_counter.called
        assert mock_metrics_collector.record_histogram.called
    
    @pytest.mark.asyncio
    async def test_batch_summarization_integration(self, summarization_service):
        """Test batch summarization with multiple texts."""
        # Arrange
        texts = {
            uuid4(): "First text to summarize. " * 10,
            uuid4(): "Second text to summarize. " * 10,
            uuid4(): "Third text to summarize. " * 10
        }
        
        # Act
        results = await summarization_service.batch_summarize(
            texts=texts,
            options={"max_length": 50}
        )
        
        # Assert
        assert len(results) == len(texts)
        for summary_id, summary in results.items():
            assert summary_id in texts
            assert isinstance(summary, str)
            assert len(summary) > 0
    
    @pytest.mark.asyncio
    async def test_batch_transcription_integration(self, transcription_service):
        """Test batch transcription with multiple audio files."""
        # Arrange
        audio_batches = {
            uuid4(): b"fake_audio_data_1" * 100,
            uuid4(): b"fake_audio_data_2" * 100,
            uuid4(): b"fake_audio_data_3" * 100
        }
        
        # Act
        results = await transcription_service.batch_transcribe(
            audio_batches=audio_batches,
            language="en",
            options={"format": "wav"}
        )
        
        # Assert
        assert len(results) == len(audio_batches)
        for transcription_id, text in results.items():
            assert transcription_id in audio_batches
            assert isinstance(text, str)
            assert len(text) > 0
    
    @pytest.mark.asyncio
    async def test_validation_error_handling_integration(self, summarization_service):
        """Test error handling and validation in integrated services."""
        # Test empty text validation
        with pytest.raises(Exception):  # ValidationError
            await summarization_service.summarize("")
        
        # Test text too short validation
        with pytest.raises(Exception):  # ValidationError
            await summarization_service.summarize("short")
        
        # Test text too long validation (if configured)
        very_long_text = "x" * 100000
        with pytest.raises(Exception):  # ValidationError
            await summarization_service.summarize(very_long_text)
    
    @pytest.mark.asyncio
    async def test_audio_validation_error_handling_integration(self, transcription_service):
        """Test audio validation error handling in integrated services."""
        # Test empty audio validation
        with pytest.raises(Exception):  # ValidationError
            await transcription_service.transcribe(b"")
        
        # Test audio too small validation
        with pytest.raises(Exception):  # ValidationError
            await transcription_service.transcribe(b"x")
        
        # Test invalid language validation
        with pytest.raises(Exception):  # ValidationError
            await transcription_service.transcribe(b"x" * 1000, language="invalid")
    
    @pytest.mark.asyncio
    async def test_metrics_collection_integration(self, summarization_service, transcription_service, mock_metrics_collector):
        """Test that metrics are properly collected across services."""
        # Summarization metrics
        await summarization_service.summarize("Test text for summarization. " * 10)
        
        # Transcription metrics
        await transcription_service.transcribe(b"fake_audio" * 100, language="en")
        
        # Verify metrics were collected for both services
        counter_calls = mock_metrics_collector.record_counter.call_args_list
        histogram_calls = mock_metrics_collector.record_histogram.call_args_list
        
        # Should have metrics for both summarization and transcription
        assert len(counter_calls) >= 2
        assert len(histogram_calls) >= 2
        
        # Verify different service metrics are recorded
        counter_names = [call[0][0] for call in counter_calls]
        assert any("summary" in name for name in counter_names)
        assert any("transcription" in name for name in counter_names)
    
    @pytest.mark.asyncio
    async def test_state_management_integration(self, summarization_service, mock_cache_service):
        """Test state management across service lifecycle."""
        summary_id = uuid4()
        
        # Process with state tracking
        await summarization_service.summarize(
            "Test text for state management. " * 10,
            summary_id=summary_id
        )
        
        # Verify state progression
        set_calls = mock_cache_service.set.call_args_list
        
        # Should have at least processing and completed states
        assert len(set_calls) >= 2
        
        # Verify state keys and data structure
        for call in set_calls:
            cache_key, state_data, ttl = call[0]
            assert f"summary_state:{summary_id}" == cache_key
            assert isinstance(state_data, dict)
            assert "status" in state_data
            assert "updated_at" in state_data
            assert isinstance(ttl, int)
    
    @pytest.mark.asyncio
    async def test_service_composition_integration(self, summarization_service, transcription_service):
        """Test that services work together in composed workflows."""
        # Simulate a workflow where transcription output is fed to summarization
        
        # Step 1: Transcribe audio
        audio_data = b"fake_audio_content" * 200
        transcribed_text = await transcription_service.transcribe(audio_data, language="en")
        
        # Step 2: Summarize transcribed text
        summary = await summarization_service.summarize(transcribed_text)
        
        # Verify the composed workflow
        assert isinstance(transcribed_text, str)
        assert isinstance(summary, str)
        assert len(summary) < len(transcribed_text)  # Summary should be shorter
        
        # Both operations should succeed
        assert len(transcribed_text) > 0
        assert len(summary) > 0
    
    def test_dependency_injection_validation(self):
        """Test that services properly validate their dependencies."""
        # Test missing dependencies raise appropriate errors
        with pytest.raises(TypeError):
            SummarizationService()  # Missing required dependencies
        
        with pytest.raises(TypeError):
            SpeechRecognitionService()  # Missing required dependencies
        
        # Test that services accept their dependencies correctly
        validator = SummaryValidator()
        metrics_service = MagicMock()
        state_manager = MagicMock()
        provider = MagicMock()
        
        # Should not raise an error with proper dependencies
        service = SummarizationService(
            summarizer_provider=provider,
            validator=validator,
            metrics_service=metrics_service,
            state_manager=state_manager
        )
        
        assert service._validator is validator
        assert service._metrics_service is metrics_service
        assert service._state_manager is state_manager
        assert service._provider is provider
    
    @pytest.mark.asyncio
    async def test_error_propagation_integration(self, mock_cache_service, mock_metrics_collector):
        """Test error propagation through the service layers."""
        # Create service with failing provider
        failing_provider = AsyncMock()
        failing_provider.provider_name = "failing_provider"
        failing_provider.summarize = AsyncMock(side_effect=Exception("Provider error"))
        
        validator = SummaryValidator()
        metrics_service = SummaryMetricsService(mock_metrics_collector)
        state_manager = SummaryStateManagerImpl(mock_cache_service)
        
        service = SummarizationService(
            summarizer_provider=failing_provider,
            validator=validator,
            metrics_service=metrics_service,
            state_manager=state_manager
        )
        
        # Test error handling
        with pytest.raises(Exception):
            await service.summarize("Test text" * 10, summary_id=uuid4())
        
        # Verify error state was recorded
        set_calls = mock_cache_service.set.call_args_list
        error_call = [call for call in set_calls if "failed" in str(call)]
        assert len(error_call) > 0  # Should have recorded failure state