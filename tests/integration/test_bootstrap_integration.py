"""
Bootstrap Integration Tests
Tests that all bootstrap modules wire dependencies correctly.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

# Bootstrap modules
from src.summarization.bootstrap import bootstrap_summarization_module
from src.transcription.bootstrap import bootstrap_transcription_module
from src.auth.bootstrap import bootstrap_auth_module
from src.analytics.bootstrap import bootstrap_analytics_module

# Required dependencies
from src.shared.events.event_bus import EventBus
from src.shared.monitoring.metrics_collector import MetricsCollector
from src.shared.infrastructure.cache import CacheService


class TestBootstrapIntegration:
    """Test bootstrap dependency injection and service wiring."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_event_bus(self):
        """Mock event bus."""
        return MagicMock(spec=EventBus)
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Mock metrics collector."""
        mock = MagicMock(spec=MetricsCollector)
        mock.record_counter = MagicMock()
        mock.record_histogram = MagicMock()
        mock.record_gauge = MagicMock()
        return mock
    
    @pytest.fixture
    def mock_cache_service(self):
        """Mock cache service."""
        mock = AsyncMock(spec=CacheService)
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_summarizer_provider(self):
        """Mock summarizer provider."""
        mock = AsyncMock()
        mock.provider_name = "test_provider"
        mock.summarize = AsyncMock(return_value="Test summary")
        return mock
    
    @pytest.fixture
    def mock_speech_provider(self):
        """Mock speech recognition provider."""
        mock = AsyncMock()
        mock.provider_name = "test_speech"
        mock.transcribe = AsyncMock(return_value="Test transcription")
        return mock
    
    @pytest.fixture
    def mock_token_service(self):
        """Mock token service."""
        mock = MagicMock()
        mock.create_access_token = MagicMock(return_value="test_token")
        mock.verify_token = MagicMock(return_value={"sub": "user123"})
        return mock
    
    @pytest.fixture
    def mock_session_service(self):
        """Mock session service."""
        mock = AsyncMock()
        mock.create_session = AsyncMock(return_value="session123")
        mock.validate_session = AsyncMock(return_value=True)
        mock.invalidate_session = AsyncMock()
        return mock
    
    @pytest.fixture
    def mock_security_service(self):
        """Mock security service."""
        mock = AsyncMock()
        mock.enforce_rate_limiting = AsyncMock(return_value=True)
        mock.detect_suspicious_activity = AsyncMock(return_value=False)
        mock.log_security_event = AsyncMock()
        return mock
    
    def test_summarization_bootstrap_wiring(
        self, 
        mock_db_session, 
        mock_event_bus, 
        mock_metrics_collector, 
        mock_cache_service,
        mock_summarizer_provider
    ):
        """Test summarization module bootstrap wiring."""
        # Act
        services = bootstrap_summarization_module(
            db_session=mock_db_session,
            event_bus=mock_event_bus,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            summarizer_provider=mock_summarizer_provider
        )
        
        # Assert - Check all expected services are created
        expected_services = [
            "summary_repository",
            "summary_queries", 
            "summary_validator",
            "summary_metrics_service",
            "summary_state_manager",
            "summarization_service",
            "request_summary_command_handler"
        ]
        
        for service_name in expected_services:
            assert service_name in services
            assert services[service_name] is not None
        
        # Test SOLID service composition
        summarization_service = services["summarization_service"]
        assert hasattr(summarization_service, '_validator')
        assert hasattr(summarization_service, '_metrics_service')
        assert hasattr(summarization_service, '_state_manager')
        assert hasattr(summarization_service, '_provider')
    
    def test_auth_bootstrap_wiring(
        self,
        mock_db_session,
        mock_metrics_collector,
        mock_cache_service,
        mock_token_service,
        mock_session_service,
        mock_security_service
    ):
        """Test auth module bootstrap wiring."""
        # Act
        services = bootstrap_auth_module(
            db_session=mock_db_session,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            token_service=mock_token_service,
            session_service=mock_session_service,
            security_service=mock_security_service
        )
        
        # Assert
        expected_services = [
            "user_repository",
            "auth_queries",
            "auth_settings",
            "auth_validator",
            "auth_metrics_service",
            "enhanced_authentication_service",
            "user_registration_service",
            "user_administration_service",
            "authentication_service"  # Legacy
        ]
        
        for service_name in expected_services:
            assert service_name in services
            assert services[service_name] is not None
        
        # Test enhanced service composition
        enhanced_auth = services["enhanced_authentication_service"]
        assert hasattr(enhanced_auth, '_validator')
        assert hasattr(enhanced_auth, '_metrics_service')
        assert hasattr(enhanced_auth, '_session_service')
        assert hasattr(enhanced_auth, '_security_service')
        assert hasattr(enhanced_auth, '_token_service')
    
    def test_transcription_bootstrap_wiring(
        self,
        mock_db_session,
        mock_metrics_collector,
        mock_cache_service,
        mock_speech_provider
    ):
        """Test transcription module bootstrap wiring."""
        # Mock additional dependencies
        mock_media_queries = MagicMock()
        mock_connection_manager = MagicMock()
        mock_storage_factory = MagicMock()
        mock_event_bus = MagicMock()
        
        # Act
        services = bootstrap_transcription_module(
            db_session=mock_db_session,
            media_queries=mock_media_queries,
            connection_manager=mock_connection_manager,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            storage_service_factory=mock_storage_factory,
            event_bus=mock_event_bus,
            speech_recognition_provider=mock_speech_provider
        )
        
        # Assert
        expected_services = [
            "transcription_repository",
            "transcription_queries",
            "transcription_validator",
            "transcription_metrics_service_enhanced", 
            "transcription_state_manager",
            "enhanced_speech_recognition_service",
            "process_transcription_handler"
        ]
        
        for service_name in expected_services:
            assert service_name in services
            assert services[service_name] is not None
        
        # Test enhanced service composition
        enhanced_speech = services["enhanced_speech_recognition_service"]
        assert hasattr(enhanced_speech, '_validator')
        assert hasattr(enhanced_speech, '_metrics_service')
        assert hasattr(enhanced_speech, '_state_manager')
        assert hasattr(enhanced_speech, '_provider')
    
    def test_analytics_bootstrap_wiring(self, mock_db_session):
        """Test analytics module bootstrap wiring."""
        # Act
        services = bootstrap_analytics_module(mock_db_session)
        
        # Assert - Check basic analytics services exist
        assert "analytics_repository" in services
        assert services["analytics_repository"] is not None
    
    def test_cross_module_dependency_compatibility(
        self,
        mock_db_session,
        mock_event_bus,
        mock_metrics_collector,
        mock_cache_service,
        mock_summarizer_provider,
        mock_speech_provider,
        mock_token_service,
        mock_session_service,
        mock_security_service
    ):
        """Test that modules can work together with shared dependencies."""
        # Bootstrap multiple modules with shared dependencies
        
        # Summarization
        sum_services = bootstrap_summarization_module(
            db_session=mock_db_session,
            event_bus=mock_event_bus,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            summarizer_provider=mock_summarizer_provider
        )
        
        # Auth
        auth_services = bootstrap_auth_module(
            db_session=mock_db_session,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            token_service=mock_token_service,
            session_service=mock_session_service,
            security_service=mock_security_service
        )
        
        # Transcription
        trans_services = bootstrap_transcription_module(
            db_session=mock_db_session,
            media_queries=MagicMock(),
            connection_manager=MagicMock(),
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            storage_service_factory=MagicMock(),
            event_bus=mock_event_bus,
            speech_recognition_provider=mock_speech_provider
        )
        
        # Assert all modules created successfully
        assert len(sum_services) > 0
        assert len(auth_services) > 0
        assert len(trans_services) > 0
        
        # Verify shared dependencies are used consistently
        # All should use the same metrics collector instance
        sum_metrics = sum_services["summary_metrics_service"]
        auth_metrics = auth_services["auth_metrics_service"]
        trans_metrics = trans_services["transcription_metrics_service_enhanced"]
        
        assert hasattr(sum_metrics, '_metrics_collector')
        assert hasattr(auth_metrics, '_metrics_collector')
        assert hasattr(trans_metrics, '_metrics_collector')
    
    def test_backward_compatibility_services(
        self,
        mock_db_session,
        mock_event_bus,
        mock_metrics_collector,
        mock_cache_service,
        mock_summarizer_provider
    ):
        """Test that legacy services are still available for backward compatibility."""
        # Bootstrap summarization
        services = bootstrap_summarization_module(
            db_session=mock_db_session,
            event_bus=mock_event_bus,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            summarizer_provider=mock_summarizer_provider
        )
        
        # Assert legacy service names still exist
        assert "summarization_metrics_service" in services  # Legacy alias
        
        # Both new and legacy should reference appropriate services
        new_service = services["summary_metrics_service"]
        legacy_service = services["summarization_metrics_service"]
        
        # In this case, they should be the same service
        assert new_service is legacy_service
    
    def test_service_configuration_validation(
        self,
        mock_db_session,
        mock_event_bus,
        mock_metrics_collector,
        mock_cache_service
    ):
        """Test that bootstrap validates service configurations."""
        # Test missing required dependencies
        with pytest.raises(TypeError):
            bootstrap_summarization_module(
                db_session=mock_db_session,
                event_bus=mock_event_bus,
                metrics_collector=mock_metrics_collector,
                cache_service=mock_cache_service
                # Missing summarizer_provider
            )
    
    def test_service_interface_compliance(
        self,
        mock_db_session,
        mock_event_bus, 
        mock_metrics_collector,
        mock_cache_service,
        mock_summarizer_provider
    ):
        """Test that bootstrapped services implement expected interfaces."""
        services = bootstrap_summarization_module(
            db_session=mock_db_session,
            event_bus=mock_event_bus,
            metrics_collector=mock_metrics_collector,
            cache_service=mock_cache_service,
            summarizer_provider=mock_summarizer_provider
        )
        
        # Test that SOLID services implement expected methods
        summarization_service = services["summarization_service"]
        
        # Should have both individual and batch methods
        assert hasattr(summarization_service, 'summarize')
        assert hasattr(summarization_service, 'batch_summarize')
        assert callable(summarization_service.summarize)
        assert callable(summarization_service.batch_summarize)
        
        # Validator should have validation methods
        validator = services["summary_validator"]
        assert hasattr(validator, 'validate_input_text')
        assert hasattr(validator, 'validate_summary_quality')
        assert callable(validator.validate_input_text)
        assert callable(validator.validate_summary_quality)