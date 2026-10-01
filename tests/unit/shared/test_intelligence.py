from unittest.mock import patch
from src.shared.infrastructure.monitoring.hardware_advisor import HardwareAdvisor, SystemPressure

class TestHardwareAdvisor:
    @patch('src.shared.infrastructure.monitoring.gpu_stats.latest', return_value=None)
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_recommend_strategy_low_pressure(self, mock_mem, mock_cpu, _gpu):
        mock_cpu.return_value = 10.0
        mock_mem.return_value.percent = 20.0

        advisor = HardwareAdvisor()

        assert advisor.recommend_strategy() == SystemPressure.LOW
        assert advisor.get_current_stats().gpu_vram_usage is None  # sem leitura: desconhecido

    @patch('src.shared.infrastructure.monitoring.gpu_stats.latest')
    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    def test_recommend_strategy_high_gpu_pressure(self, mock_mem, mock_cpu, mock_gpu):
        from src.shared.infrastructure.monitoring.gpu_stats import GpuReading

        mock_cpu.return_value = 10.0
        mock_mem.return_value.percent = 20.0
        # 90% da placa ocupada (por exemplo, Ollama + Whisper)
        mock_gpu.return_value = GpuReading(memory_used_mb=11059, memory_total_mb=12288, utilization_percent=97)

        advisor = HardwareAdvisor(vram_threshold_high=0.80)

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
