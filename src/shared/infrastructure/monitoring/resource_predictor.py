"""Motor de Observabilidade Preditiva."""
from __future__ import annotations

import structlog
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger(__name__)

class RiskLevel(str, Enum):
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    TERMINAL = "terminal"

@dataclass
class CostPrediction:
    estimated_duration_seconds: float
    vram_required_gb: float
    risk_level: RiskLevel
    recommendation: str

class ResourcePredictor:
    """Prediz o consumo de recursos antes da execução (Observabilidade Preditiva)."""

    # Benchmarks empíricos (exemplo: Llama 3 8B consome ~5.5GB em 4-bit)
    VRAM_BASE_LOAD = 5.5 
    VRAM_PER_1000_CHARS = 0.05
    TIME_PER_CHUNK_SECONDS = 8.0 # Média de geração por tópico

    def predict_analysis_cost(self, text_length: int, num_topics_hint: int = 5) -> CostPrediction:
        """Estima o custo de uma análise de texto."""
        
        # Cálculo de VRAM estimada
        vram_est = self.VRAM_BASE_LOAD + (text_length / 1000 * self.VRAM_PER_1000_CHARS)
        
        # Tempo estimado
        duration_est = num_topics_hint * self.TIME_PER_CHUNK_SECONDS
        
        # Avaliação de Risco
        risk = RiskLevel.SAFE
        recommendation = "Proceed with high-quality models."
        
        if vram_est > 10.0: # Ex: Limite de uma RTX 3060 12GB
            risk = RiskLevel.DANGEROUS
            recommendation = "High risk of OOM. Suggest model quantization or chunk reduction."
        
        if text_length > 100000: # Textos gigantes
            risk = RiskLevel.WARNING
            recommendation = "Long processing time predicted. Background execution recommended."

        return CostPrediction(
            estimated_duration_seconds=duration_est,
            vram_required_gb=vram_est,
            risk_level=risk,
            recommendation=recommendation
        )

    def predict_transcription_cost(self, duration_seconds: float) -> CostPrediction:
        """Estima o custo de uma transcrição via Whisper."""
        # Whisper Large-v3 consome ~4.5GB VRAM fixa + picos
        vram_est = 4.5 if duration_seconds < 1800 else 6.0
        
        # Whisper costuma processar 10x mais rápido que o tempo real na GPU
        duration_est = duration_seconds / 10
        
        risk = RiskLevel.SAFE
        if duration_seconds > 3600: # > 1 hora
            risk = RiskLevel.WARNING
            
        return CostPrediction(
            estimated_duration_seconds=duration_est,
            vram_required_gb=vram_est,
            risk_level=risk,
            recommendation="Auto-scaling might be needed for hour-long media."
        )
