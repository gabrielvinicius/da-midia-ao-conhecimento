"""Abstração para passos do pipeline de análise de texto."""
from __future__ import annotations

import structlog
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from src.text_analysis.domain import Analysis

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=Analysis)


class AnalysisStep(ABC, Generic[T]):
    """Contrato para um passo individual de análise."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome do passo para logs e métricas."""
        ...

    @abstractmethod
    async def process(self, analysis: T) -> T:
        """Executa a lógica do passo e retorna a análise atualizada.
        
        Deve lançar exceções apenas se o erro for fatal para todo o pipeline.
        Erros parciais devem ser logados e a análise retornada com o estado possível.
        """
        ...


class AnalysisPipeline:
    """Orquestrador sequencial de passos."""

    def __init__(self, steps: list[AnalysisStep]):
        self.steps = steps

    async def run(self, analysis: Analysis) -> Analysis:
        for step in self.steps:
            logger.info("pipeline.step_start", step=step.name, analysis_id=str(analysis.id))
            try:
                analysis = await step.process(analysis)
            except Exception as exc:
                logger.error(
                    "pipeline.step_failed",
                    step=step.name,
                    analysis_id=str(analysis.id),
                    error=str(exc),
                )
                # Decisão de design: Continuar o pipeline ou parar?
                # Como implementamos resiliência parcial, vamos continuar, 
                # mas o passo falho deve garantir que não quebrou a integridade do objeto.
        return analysis
