"""
Performance Monitoring Tests for SOLID Architecture
Tests performance characteristics of the refactored services.
"""
import pytest
import time
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from statistics import mean, median

# SOLID services for performance testing
from src.summarization.application.services.summarization_service import SummarizationService
from src.summarization.application.services.summary_validator import SummaryValidator
from src.summarization.application.services.summary_metrics_service import SummaryMetricsService
from src.summarization.application.services.summary_state_manager_impl import SummaryStateManagerImpl

from src.transcription.application.services.speech_recognition_service import SpeechRecognitionService
from src.transcription.application.services.transcription_validator import TranscriptionValidator
from src.transcription.application.services.transcription_metrics_service_impl import TranscriptionMetricsServiceImpl
from src.transcription.application.services.transcription_state_manager_impl import TranscriptionStateManagerImpl


class TestSOLIDPerformanceMonitoring:
    """Performance monitoring tests for SOLID architecture."""
    
    @pytest.fixture
    def performance_environment(self):
        """Set up performance testing environment."""
        # Mock dependencies
        mock_metrics_collector = MagicMock()
        mock_cache_service = AsyncMock()
        mock_cache_service.get.return_value = None
        mock_cache_service.set = AsyncMock()
        
        # Fast mock providers
        mock_summarizer = AsyncMock()
        mock_summarizer.provider_name = "fast_provider"
        mock_summarizer.summarize = AsyncMock(return_value="Fast summary response")
        
        mock_speech_provider = AsyncMock()
        mock_speech_provider.provider_name = "fast_speech"
        mock_speech_provider.transcribe = AsyncMock(return_value="Fast transcription response")
        
        # Create SOLID services
        summary_validator = SummaryValidator(min_text_length=10, max_text_length=10000)
        summary_metrics = SummaryMetricsService(mock_metrics_collector)
        summary_state = SummaryStateManagerImpl(mock_cache_service)
        
        summarization_service = SummarizationService(
            summarizer_provider=mock_summarizer,
            validator=summary_validator,
            metrics_service=summary_metrics,
            state_manager=summary_state
        )
        
        transcription_validator = TranscriptionValidator(
            min_audio_size=100,
            max_audio_size=1000000,
            supported_languages={"en", "es", "fr"}
        )
        transcription_metrics = TranscriptionMetricsServiceImpl(mock_metrics_collector)
        transcription_state = TranscriptionStateManagerImpl(mock_cache_service)
        
        transcription_service = SpeechRecognitionService(
            speech_recognition_provider=mock_speech_provider,
            validator=transcription_validator,
            metrics_service=transcription_metrics,
            state_manager=transcription_state
        )
        
        return {
            "summarization_service": summarization_service,
            "transcription_service": transcription_service,
            "mocks": {
                "summarizer": mock_summarizer,
                "speech_provider": mock_speech_provider,
                "cache_service": mock_cache_service,
                "metrics_collector": mock_metrics_collector
            }
        }
    
    @pytest.mark.asyncio
    async def test_single_request_performance(self, performance_environment):
        """Test performance of single requests."""
        env = performance_environment
        
        # Test summarization performance
        start_time = time.time()
        await env["summarization_service"].summarize("Test text for summarization. " * 10)
        summarization_duration = time.time() - start_time
        
        # Test transcription performance
        start_time = time.time()
        await env["transcription_service"].transcribe(b"audio_data" * 100, language="en")
        transcription_duration = time.time() - start_time
        
        # Performance assertions (should be fast with mocks)
        assert summarization_duration < 0.1  # Should complete within 100ms
        assert transcription_duration < 0.1  # Should complete within 100ms
        
        print(f"Summarization duration: {summarization_duration:.4f}s")
        print(f"Transcription duration: {transcription_duration:.4f}s")
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, performance_environment):
        """Test performance of batch processing."""
        env = performance_environment
        
        # Prepare batch data
        batch_size = 10
        texts = {uuid4(): f"Text to summarize {i}. " * 10 for i in range(batch_size)}
        audio_batches = {uuid4(): f"audio_data_{i}".encode() * 100 for i in range(batch_size)}
        
        # Test batch summarization performance
        start_time = time.time()
        summary_results = await env["summarization_service"].batch_summarize(texts)
        batch_summarization_duration = time.time() - start_time
        
        # Test batch transcription performance
        start_time = time.time()
        transcription_results = await env["transcription_service"].batch_transcribe(audio_batches, language="en")
        batch_transcription_duration = time.time() - start_time
        
        # Performance assertions
        assert len(summary_results) == batch_size
        assert len(transcription_results) == batch_size
        assert batch_summarization_duration < 1.0  # Should complete within 1 second
        assert batch_transcription_duration < 1.0  # Should complete within 1 second
        
        # Calculate per-item performance
        avg_summary_time = batch_summarization_duration / batch_size
        avg_transcription_time = batch_transcription_duration / batch_size
        
        print(f"Batch summarization: {batch_summarization_duration:.4f}s total, {avg_summary_time:.4f}s per item")
        print(f"Batch transcription: {batch_transcription_duration:.4f}s total, {avg_transcription_time:.4f}s per item")
    
    @pytest.mark.asyncio
    async def test_concurrent_processing_performance(self, performance_environment):
        """Test performance under concurrent load."""
        env = performance_environment
        
        concurrent_requests = 5
        
        # Create concurrent summarization tasks
        summary_tasks = []
        for i in range(concurrent_requests):
            task = env["summarization_service"].summarize(
                f"Concurrent test text {i}. " * 10,
                summary_id=uuid4()
            )
            summary_tasks.append(task)
        
        # Create concurrent transcription tasks
        transcription_tasks = []
        for i in range(concurrent_requests):
            task = env["transcription_service"].transcribe(
                f"concurrent_audio_{i}".encode() * 100,
                language="en",
                transcription_id=uuid4()
            )
            transcription_tasks.append(task)
        
        # Execute concurrent tasks
        start_time = time.time()
        summary_results = await asyncio.gather(*summary_tasks)
        concurrent_summary_duration = time.time() - start_time
        
        start_time = time.time()
        transcription_results = await asyncio.gather(*transcription_tasks)
        concurrent_transcription_duration = time.time() - start_time
        
        # Performance assertions
        assert len(summary_results) == concurrent_requests
        assert len(transcription_results) == concurrent_requests
        assert concurrent_summary_duration < 0.5  # Should handle concurrency efficiently
        assert concurrent_transcription_duration < 0.5
        
        print(f"Concurrent summarization: {concurrent_summary_duration:.4f}s for {concurrent_requests} requests")
        print(f"Concurrent transcription: {concurrent_transcription_duration:.4f}s for {concurrent_requests} requests")
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, performance_environment):
        """Test memory usage characteristics."""
        import psutil
        import os
        
        env = performance_environment
        process = psutil.Process(os.getpid())
        
        # Baseline memory
        baseline_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Process multiple requests to check for memory leaks
        for i in range(20):
            await env["summarization_service"].summarize(f"Memory test text {i}. " * 20)
            await env["transcription_service"].transcribe(f"memory_audio_{i}".encode() * 200, language="en")
        
        # Final memory
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - baseline_memory
        
        print(f"Memory usage - Baseline: {baseline_memory:.2f}MB, Final: {final_memory:.2f}MB")
        print(f"Memory increase: {memory_increase:.2f}MB")
        
        # Memory increase should be reasonable (less than 50MB for test)
        assert memory_increase < 50, f"Memory increase too high: {memory_increase}MB"
    
    @pytest.mark.asyncio
    async def test_validation_performance_impact(self, performance_environment):
        """Test performance impact of validation layers."""
        env = performance_environment
        
        # Test with validation (normal flow)
        start_time = time.time()
        await env["summarization_service"].summarize("Test text with validation. " * 15)
        with_validation_duration = time.time() - start_time
        
        # Test direct provider call (bypass validation)
        start_time = time.time()
        await env["mocks"]["summarizer"].summarize("Test text without validation. " * 15)
        without_validation_duration = time.time() - start_time
        
        # Calculate validation overhead
        validation_overhead = with_validation_duration - without_validation_duration
        overhead_percentage = (validation_overhead / without_validation_duration) * 100
        
        print(f"With validation: {with_validation_duration:.6f}s")
        print(f"Without validation: {without_validation_duration:.6f}s")
        print(f"Validation overhead: {validation_overhead:.6f}s ({overhead_percentage:.2f}%)")
        
        # Validation overhead should be minimal
        assert overhead_percentage < 500, f"Validation overhead too high: {overhead_percentage:.2f}%"
    
    @pytest.mark.asyncio
    async def test_metrics_collection_performance_impact(self, performance_environment):
        """Test performance impact of metrics collection."""
        env = performance_environment
        metrics_collector = env["mocks"]["metrics_collector"]
        
        # Measure with metrics collection
        start_time = time.time()
        await env["summarization_service"].summarize("Test text for metrics. " * 15, summary_id=uuid4())
        with_metrics_duration = time.time() - start_time
        
        # Verify metrics were collected
        assert metrics_collector.record_counter.called
        assert metrics_collector.record_histogram.called
        
        # Reset metrics mock
        metrics_collector.reset_mock()
        
        # Measure without metrics (direct provider)
        start_time = time.time()
        await env["mocks"]["summarizer"].summarize("Test text without metrics. " * 15)
        without_metrics_duration = time.time() - start_time
        
        # Calculate metrics overhead
        metrics_overhead = with_metrics_duration - without_metrics_duration
        overhead_percentage = (metrics_overhead / without_metrics_duration) * 100
        
        print(f"With metrics: {with_metrics_duration:.6f}s")
        print(f"Without metrics: {without_metrics_duration:.6f}s")
        print(f"Metrics overhead: {metrics_overhead:.6f}s ({overhead_percentage:.2f}%)")
        
        # Metrics overhead should be reasonable
        assert overhead_percentage < 1000, f"Metrics overhead too high: {overhead_percentage:.2f}%"
    
    @pytest.mark.asyncio
    async def test_state_management_performance_impact(self, performance_environment):
        """Test performance impact of state management."""
        env = performance_environment
        cache_service = env["mocks"]["cache_service"]
        
        # Test with state management
        start_time = time.time()
        await env["summarization_service"].summarize("Test text with state. " * 15, summary_id=uuid4())
        with_state_duration = time.time() - start_time
        
        # Test without state management (no summary_id)
        start_time = time.time()
        await env["summarization_service"].summarize("Test text without state. " * 15)
        without_state_duration = time.time() - start_time
        
        # Verify state calls were made
        assert cache_service.set.called
        
        # Calculate state management overhead
        state_overhead = with_state_duration - without_state_duration
        overhead_percentage = (state_overhead / without_state_duration) * 100
        
        print(f"With state management: {with_state_duration:.6f}s")
        print(f"Without state management: {without_state_duration:.6f}s")
        print(f"State overhead: {state_overhead:.6f}s ({overhead_percentage:.2f}%)")
        
        # State management overhead should be reasonable
        assert overhead_percentage < 1000, f"State overhead too high: {overhead_percentage:.2f}%"
    
    @pytest.mark.asyncio
    async def test_error_handling_performance(self, performance_environment):
        """Test performance characteristics during error scenarios."""
        env = performance_environment
        
        # Test validation error performance
        validation_error_times = []
        for i in range(5):
            start_time = time.time()
            try:
                await env["summarization_service"].summarize("")  # Should fail validation
            except Exception:
                pass
            validation_error_times.append(time.time() - start_time)
        
        # Test provider error performance
        env["mocks"]["summarizer"].summarize.side_effect = Exception("Provider error")
        
        provider_error_times = []
        for i in range(5):
            start_time = time.time()
            try:
                await env["summarization_service"].summarize("Test text. " * 10, summary_id=uuid4())
            except Exception:
                pass
            provider_error_times.append(time.time() - start_time)
        
        # Calculate error handling performance
        avg_validation_error_time = mean(validation_error_times)
        avg_provider_error_time = mean(provider_error_times)
        
        print(f"Average validation error time: {avg_validation_error_time:.6f}s")
        print(f"Average provider error time: {avg_provider_error_time:.6f}s")
        
        # Error handling should be fast
        assert avg_validation_error_time < 0.01  # Validation errors should be very fast
        assert avg_provider_error_time < 0.1   # Provider errors should be reasonably fast