import pytest
from unittest.mock import MagicMock, patch
from src.shared.infrastructure.monitoring.hardware_advisor import HardwareAdvisor, SystemPressure
from src.shared.infrastructure.monitoring.resource_predictor import ResourcePredictor, RiskLevel

class TestHardwareAdvisor:
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('torch.cuda.is_available')
    def test_recommend_strategy_low_pressure(self, mock_cuda, mock_mem, mock_cpu):
        # Arrange
        mock_cpu.return_value = 10.0
        mock_mem.return_value.percent = 20.0
        mock_cuda.return_value = False
        
        advisor = HardwareAdvisor()
        
        # Act
        strategy = advisor.recommend_strategy()
        
        # Assert
        assert strategy == SystemPressure.LOW

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('torch.cuda.is_available')
    @patch('torch.cuda.get_device_properties')
    @patch('torch.cuda.memory_allocated')
    @patch('torch.cuda.memory_reserved')
    def test_recommend_strategy_high_gpu_pressure(self, mock_res, mock_alloc, mock_prop, mock_cuda, mock_mem, mock_cpu):
        # Arrange
        mock_cpu.return_value = 10.0
        mock_mem.return_value.percent = 20.0
        mock_cuda.return_value = True
        
        # Simulate 90% VRAM usage
        mock_prop.return_value.total_memory = 1000
        mock_alloc.return_value = 450
        mock_res.return_value = 450
        
        advisor = HardwareAdvisor(vram_threshold_high=0.80)
        
        # Act
        strategy = advisor.recommend_strategy()
        
        # Assert
        assert strategy == SystemPressure.HIGH

    def test_circuit_breaker_quarantine(self):
        # Arrange
        advisor = HardwareAdvisor(failure_threshold=2)
        provider = "test-ai"
        
        # Act & Assert
        assert advisor.is_provider_healthy(provider) is True
        
        advisor.report_failure(provider)
        assert advisor.is_provider_healthy(provider) is True
        
        advisor.report_failure(provider)
        # Now it should be unhealthy (consecutive failures >= threshold)
        assert advisor.is_provider_healthy(provider) is False
        
        advisor.report_success(provider)
        assert advisor.is_provider_healthy(provider) is True

class TestResourcePredictor:
    def test_predict_analysis_cost_safe(self):
        predictor = ResourcePredictor()
        # Small text
        prediction = predictor.predict_analysis_cost(1000)
        
        assert prediction.risk_level == RiskLevel.SAFE
        assert prediction.vram_required_gb < 6.0

    def test_predict_analysis_cost_dangerous(self):
        predictor = ResourcePredictor()
        # Very large text (~100k chars)
        prediction = predictor.predict_analysis_cost(100000)
        
        assert prediction.risk_level == RiskLevel.DANGEROUS
        assert "OOM" in prediction.recommendation

    def test_predict_transcription_cost(self):
        predictor = ResourcePredictor()
        # 10 minutes video
        prediction = predictor.predict_transcription_cost(600)
        
        assert prediction.risk_level == RiskLevel.SAFE
        assert prediction.estimated_duration_seconds == 60.0 # 10x faster than real time
