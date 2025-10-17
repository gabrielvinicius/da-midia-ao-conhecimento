"""
End-to-End SOLID Architecture Tests
Tests complete workflows using the refactored SOLID services.
"""
import pytest
import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import io

# SOLID services for E2E testing
from src.summarization.bootstrap import bootstrap_summarization_module
from src.transcription.bootstrap import bootstrap_transcription_module
from src.auth.bootstrap import bootstrap_auth_module
from src.analytics.bootstrap import bootstrap_analytics_module

# Infrastructure mocks
from tests.mocks.in_memory_storage import InMemoryStorage
from tests.mocks.in_memory_event_bus import InMemoryEventBus


class TestSOLIDEndToEndWorkflows:
    """End-to-end tests for complete SOLID architecture workflows."""
    
    @pytest.fixture
    async def complete_solid_environment(self):
        """Set up complete SOLID environment with all modules."""
        # Mock infrastructure dependencies
        mock_db_session = AsyncMock()
        mock_event_bus = InMemoryEventBus()
        mock_metrics_collector = MagicMock()
        mock_cache_service = AsyncMock()
        
        # Mock providers
        mock_summarizer = AsyncMock()
        mock_summarizer.provider_name = "test_summarizer"
        mock_summarizer.summarize = AsyncMock()
        
        mock_speech_provider = AsyncMock()
        mock_speech_provider.provider_name = "test_speech"
        mock_speech_provider.transcribe = AsyncMock()
        
        mock_token_service = MagicMock()
        mock_session_service = AsyncMock()
        mock_security_service = AsyncMock()
        
        # Bootstrap all modules
        summarization_services = bootstrap_summarization_module(
            db_session=mock_db_session,
            event_bus=mock_event_bus,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            summarizer_provider=mock_summarizer
        )
        
        auth_services = bootstrap_auth_module(
            db_session=mock_db_session,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            token_service=mock_token_service,
            session_service=mock_session_service,
            security_service=mock_security_service
        )
        
        transcription_services = bootstrap_transcription_module(
            db_session=mock_db_session,
            media_queries=MagicMock(),
            connection_manager=MagicMock(),
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            storage_service_factory=MagicMock(),
            event_bus=mock_event_bus,
            speech_recognition_provider=mock_speech_provider
        )
        
        analytics_services = bootstrap_analytics_module(mock_db_session)
        
        return {
            "summarization": summarization_services,
            "auth": auth_services,
            "transcription": transcription_services,
            "analytics": analytics_services,
            "mocks": {
                "summarizer": mock_summarizer,
                "speech_provider": mock_speech_provider,
                "cache_service": mock_cache_service,
                "metrics_collector": mock_metrics_collector,
                "security_service": mock_security_service,
                "session_service": mock_session_service,
                "token_service": mock_token_service
            }
        }
    
    @pytest.mark.asyncio
    async def test_complete_media_processing_workflow(self, complete_solid_environment):
        """Test complete media processing: authentication -> transcription -> summarization."""
        env = complete_solid_environment
        
        # Setup mock responses
        env["mocks"]["speech_provider"].transcribe.return_value = (
            "This is a long transcribed text from audio content. "
            "It contains multiple sentences and detailed information. " * 5
        )
        env["mocks"]["summarizer"].summarize.return_value = (
            "This is a concise summary of the transcribed audio content."
        )
        env["mocks"]["security_service"].enforce_rate_limiting.return_value = True
        env["mocks"]["security_service"].detect_suspicious_activity.return_value = False
        env["mocks"]["session_service"].create_session.return_value = "session123"
        
        # Step 1: Enhanced Authentication
        auth_service = env["auth"]["enhanced_authentication_service"]
        auth_result = await auth_service.authenticate_with_validation(
            email="test@example.com",
            password="SecurePassword123!",
            ip_address="192.168.1.100",
            user_agent="TestClient/1.0"
        )
        
        assert "access_token" in auth_result
        assert "session_id" in auth_result
        assert auth_result["session_id"] == "session123"
        
        # Step 2: Audio Transcription with SOLID services
        transcription_service = env["transcription"]["enhanced_speech_recognition_service"]
        audio_data = b"fake_audio_content" * 200  # Sufficient size
        
        transcription_result = await transcription_service.transcribe(
            audio_bytes=audio_data,
            language="en",
            transcription_id=uuid4(),
            options={"format": "wav"}
        )
        
        assert isinstance(transcription_result, str)
        assert len(transcription_result) > 0
        
        # Step 3: Text Summarization with SOLID services
        summarization_service = env["summarization"]["summarization_service"]
        summary_result = await summarization_service.summarize(
            text_content=transcription_result,
            summary_id=uuid4(),
            options={"max_length": 150}
        )
        
        assert isinstance(summary_result, str)
        assert len(summary_result) > 0
        assert len(summary_result) < len(transcription_result)
        
        # Verify all services were called correctly
        env["mocks"]["speech_provider"].transcribe.assert_called_once()
        env["mocks"]["summarizer"].summarize.assert_called_once()
        env["mocks"]["session_service"].create_session.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_batch_processing_workflow(self, complete_solid_environment):
        """Test batch processing workflow with multiple items."""
        env = complete_solid_environment
        
        # Setup batch data
        audio_batches = {
            uuid4(): b"audio_content_1" * 100,
            uuid4(): b"audio_content_2" * 100,
            uuid4(): b"audio_content_3" * 100
        }
        
        # Mock transcription responses
        transcription_responses = [
            "Transcribed content from audio 1. " * 10,
            "Transcribed content from audio 2. " * 10,
            "Transcribed content from audio 3. " * 10
        ]
        env["mocks"]["speech_provider"].transcribe.side_effect = transcription_responses
        
        # Mock summarization responses  
        summary_responses = [
            "Summary of audio 1.",
            "Summary of audio 2.", 
            "Summary of audio 3."
        ]
        env["mocks"]["summarizer"].summarize.side_effect = summary_responses
        
        # Step 1: Batch transcription
        transcription_service = env["transcription"]["enhanced_speech_recognition_service"]
        transcription_results = await transcription_service.batch_transcribe(
            audio_batches=audio_batches,
            language="en",
            options={"format": "wav"}
        )
        
        assert len(transcription_results) == len(audio_batches)
        
        # Step 2: Batch summarization of transcribed texts
        summarization_service = env["summarization"]["summarization_service"]
        summary_results = await summarization_service.batch_summarize(
            texts=transcription_results,
            options={"max_length": 100}
        )
        
        assert len(summary_results) == len(transcription_results)
        
        # Verify batch processing worked correctly
        assert env["mocks"]["speech_provider"].transcribe.call_count == len(audio_batches)
        assert env["mocks"]["summarizer"].summarize.call_count == len(transcription_results)
    
    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, complete_solid_environment):
        """Test error handling across the complete workflow."""
        env = complete_solid_environment
        
        # Test authentication failure
        env["mocks"]["security_service"].enforce_rate_limiting.return_value = False
        
        auth_service = env["auth"]["enhanced_authentication_service"]
        with pytest.raises(Exception):  # Should raise ValidationError for rate limiting
            await auth_service.authenticate_with_validation(
                email="test@example.com",
                password="password",
                ip_address="192.168.1.100",
                user_agent="TestClient/1.0"
            )
        
        # Test transcription validation failure
        transcription_service = env["transcription"]["enhanced_speech_recognition_service"]
        with pytest.raises(Exception):  # Should raise ValidationError for empty audio
            await transcription_service.transcribe(b"")
        
        # Test summarization validation failure
        summarization_service = env["summarization"]["summarization_service"]
        with pytest.raises(Exception):  # Should raise ValidationError for empty text
            await summarization_service.summarize("")
    
    @pytest.mark.asyncio
    async def test_metrics_collection_workflow(self, complete_solid_environment):
        """Test metrics collection across the complete workflow."""
        env = complete_solid_environment
        metrics_collector = env["mocks"]["metrics_collector"]
        
        # Setup successful responses
        env["mocks"]["speech_provider"].transcribe.return_value = "Transcribed text. " * 20
        env["mocks"]["summarizer"].summarize.return_value = "Summary text."
        env["mocks"]["security_service"].enforce_rate_limiting.return_value = True
        env["mocks"]["security_service"].detect_suspicious_activity.return_value = False
        env["mocks"]["session_service"].create_session.return_value = "session123"
        
        # Execute workflow
        auth_service = env["auth"]["enhanced_authentication_service"]
        await auth_service.authenticate_with_validation(
            email="test@example.com",
            password="SecurePassword123!",
            ip_address="192.168.1.100",
            user_agent="TestClient/1.0"
        )
        
        transcription_service = env["transcription"]["enhanced_speech_recognition_service"]
        transcribed_text = await transcription_service.transcribe(
            audio_bytes=b"audio" * 100,
            language="en"
        )
        
        summarization_service = env["summarization"]["summarization_service"]
        await summarization_service.summarize(transcribed_text)
        
        # Verify metrics were collected from all services
        assert metrics_collector.record_counter.call_count >= 3  # Auth, transcription, summarization
        assert metrics_collector.record_histogram.call_count >= 2  # Processing times
        
        # Check specific metric types
        counter_calls = [call[0][0] for call in metrics_collector.record_counter.call_args_list]
        assert any("auth" in metric for metric in counter_calls)
        assert any("transcription" in metric for metric in counter_calls)
        assert any("summary" in metric for metric in counter_calls)
    
    @pytest.mark.asyncio
    async def test_state_management_workflow(self, complete_solid_environment):
        """Test state management across the complete workflow."""
        env = complete_solid_environment
        cache_service = env["mocks"]["cache_service"]
        
        # Setup responses
        env["mocks"]["speech_provider"].transcribe.return_value = "Transcribed content. " * 15
        env["mocks"]["summarizer"].summarize.return_value = "Summary content."
        
        # Execute workflow with state tracking
        transcription_id = uuid4()
        summary_id = uuid4()
        
        transcription_service = env["transcription"]["enhanced_speech_recognition_service"]
        await transcription_service.transcribe(
            audio_bytes=b"audio" * 100,
            language="en",
            transcription_id=transcription_id
        )
        
        summarization_service = env["summarization"]["summarization_service"]
        await summarization_service.summarize(
            text_content="Text to summarize. " * 20,
            summary_id=summary_id
        )
        
        # Verify state management calls
        set_calls = cache_service.set.call_args_list
        
        # Should have state updates for both processes
        transcription_states = [call for call in set_calls if f"transcription_state:{transcription_id}" in str(call)]
        summary_states = [call for call in set_calls if f"summary_state:{summary_id}" in str(call)]
        
        assert len(transcription_states) >= 2  # processing + completed
        assert len(summary_states) >= 2  # processing + completed
    
    @pytest.mark.asyncio
    async def test_security_monitoring_workflow(self, complete_solid_environment):
        """Test security monitoring throughout the workflow."""
        env = complete_solid_environment
        security_service = env["mocks"]["security_service"]
        
        # Setup security responses
        security_service.enforce_rate_limiting.return_value = True
        security_service.detect_suspicious_activity.return_value = True  # Flag as suspicious
        env["mocks"]["session_service"].create_session.return_value = "session123"
        
        # Execute authentication with security monitoring
        auth_service = env["auth"]["enhanced_authentication_service"]
        result = await auth_service.authenticate_with_validation(
            email="test@example.com",
            password="SecurePassword123!",
            ip_address="192.168.1.100",
            user_agent="SuspiciousClient/1.0"
        )
        
        # Verify security checks were performed
        security_service.enforce_rate_limiting.assert_called_once_with("192.168.1.100", "login")
        security_service.detect_suspicious_activity.assert_called_once()
        security_service.log_security_event.assert_called_once()
        
        # Verify security flags in response
        assert "security_flags" in result
        assert result["security_flags"]["suspicious_activity"] is True
    
    @pytest.mark.asyncio
    async def test_validation_integration_workflow(self, complete_solid_environment):
        """Test validation integration across all services."""
        env = complete_solid_environment
        
        # Test validation chain: auth -> transcription -> summarization
        
        # 1. Auth validation
        auth_service = env["auth"]["enhanced_authentication_service"]
        
        # Should fail with invalid email
        with pytest.raises(Exception):
            await auth_service.authenticate_with_validation(
                email="invalid-email",
                password="password",
                ip_address="192.168.1.100",
                user_agent="TestClient/1.0"
            )
        
        # 2. Transcription validation
        transcription_service = env["transcription"]["enhanced_speech_recognition_service"]
        
        # Should fail with invalid language
        with pytest.raises(Exception):
            await transcription_service.transcribe(
                audio_bytes=b"audio" * 100,
                language="invalid_language"
            )
        
        # 3. Summarization validation
        summarization_service = env["summarization"]["summarization_service"]
        
        # Should fail with text too short
        with pytest.raises(Exception):
            await summarization_service.summarize("short")
    
    @pytest.mark.asyncio
    async def test_performance_monitoring_workflow(self, complete_solid_environment):
        """Test performance monitoring across the workflow."""
        env = complete_solid_environment
        metrics_collector = env["mocks"]["metrics_collector"]
        
        # Setup responses with timing
        env["mocks"]["speech_provider"].transcribe.return_value = "Transcribed text. " * 25
        env["mocks"]["summarizer"].summarize.return_value = "Summary text."
        env["mocks"]["security_service"].enforce_rate_limiting.return_value = True
        env["mocks"]["security_service"].detect_suspicious_activity.return_value = False
        env["mocks"]["session_service"].create_session.return_value = "session123"
        
        # Execute timed workflow
        start_time = datetime.utcnow()
        
        # Authentication
        auth_service = env["auth"]["enhanced_authentication_service"]
        await auth_service.authenticate_with_validation(
            email="test@example.com",
            password="SecurePassword123!",
            ip_address="192.168.1.100",
            user_agent="TestClient/1.0"
        )
        
        # Transcription
        transcription_service = env["transcription"]["enhanced_speech_recognition_service"]
        transcribed_text = await transcription_service.transcribe(
            audio_bytes=b"audio" * 200,
            language="en",
            transcription_id=uuid4()
        )
        
        # Summarization
        summarization_service = env["summarization"]["summarization_service"]
        await summarization_service.summarize(
            text_content=transcribed_text,
            summary_id=uuid4()
        )
        
        end_time = datetime.utcnow()
        total_duration = (end_time - start_time).total_seconds()
        
        # Verify performance metrics were recorded
        histogram_calls = metrics_collector.record_histogram.call_args_list
        
        # Should have duration metrics for transcription and summarization
        duration_metrics = [call for call in histogram_calls if "duration" in call[0][0]]
        assert len(duration_metrics) >= 2
        
        # Verify reasonable total processing time
        assert total_duration < 5.0  # Should complete quickly in test environment
    
    @pytest.mark.asyncio 
    async def test_session_lifecycle_workflow(self, complete_solid_environment):
        """Test complete session lifecycle with SOLID services."""
        env = complete_solid_environment
        session_service = env["mocks"]["session_service"]
        
        # Setup session responses
        session_service.create_session.return_value = "session123"
        session_service.validate_session.return_value = True
        env["mocks"]["security_service"].enforce_rate_limiting.return_value = True
        env["mocks"]["security_service"].detect_suspicious_activity.return_value = False
        
        # Step 1: Login and create session
        auth_service = env["auth"]["enhanced_authentication_service"]
        login_result = await auth_service.authenticate_with_validation(
            email="test@example.com",
            password="SecurePassword123!",
            ip_address="192.168.1.100",
            user_agent="TestClient/1.0"
        )
        
        session_id = login_result["session_id"]
        user_id = uuid4()
        
        # Step 2: Use session for operations (implicit validation)
        # In real scenario, middleware would validate session
        
        # Step 3: Logout single session
        await auth_service.logout_user(user_id, session_id)
        session_service.invalidate_session.assert_called_once_with(session_id)
        
        # Step 4: Logout all sessions
        session_service.invalidate_all_user_sessions.return_value = 3
        invalidated_count = await auth_service.logout_all_sessions(user_id)
        
        assert invalidated_count == 3
        session_service.invalidate_all_user_sessions.assert_called_once_with(user_id)