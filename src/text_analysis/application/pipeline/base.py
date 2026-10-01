"""Abstração para passos do pipeline de análise de texto."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Awaitable, Callable, Generic, Optional, TypeVar

import time

import structlog

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


StepCallback = Callable[[Analysis, str], Awaitable[None]]


class AnalysisPipeline:
    """Orquestrador sequencial de passos.

    A falha de um passo não interrompe os seguintes: ela é registrada em
    ``analysis.diagnostics["steps"]`` e o pipeline continua com o estado já
    produzido. Se ``on_step_completed`` for informado, ele é chamado ao fim de
    cada passo (com sucesso ou falha), o que permite salvar os resultados
    parciais à medida que são gerados.
    """

    def __init__(self, steps: list[AnalysisStep], release_after_run: Optional[list] = None):
        self.steps = steps
        # Recursos liberados ao fim de cada execução, com sucesso ou não (ex.:
        # o modelo de linguagem no Ollama, que não deve ficar ocupando a GPU
        # enquanto a próxima mídia é transcrita).
        self.release_after_run = release_after_run or []

    async def run(
        self,
        analysis: Analysis,
        on_step_completed: Optional[StepCallback] = None,
    ) -> Analysis:
        try:
            return await self._run_steps(analysis, on_step_completed)
        finally:
            for resource in self.release_after_run:
                try:
                    await resource.release()
                except Exception as exc:
                    logger.warning("pipeline.release_failed", error=str(exc))

    async def _run_steps(
        self,
        analysis: Analysis,
        on_step_completed: Optional[StepCallback],
    ) -> Analysis:
        statuses = analysis.diagnostics.setdefault("steps", {})
        durations = analysis.diagnostics.setdefault("step_seconds", {})
        for step in self.steps:
            logger.info("pipeline.step_start", step=step.name, analysis_id=str(analysis.id))
            started = time.perf_counter()
            try:
                analysis = await step.process(analysis)
                statuses = analysis.diagnostics.setdefault("steps", statuses)
                durations = analysis.diagnostics.setdefault("step_seconds", durations)
                statuses[step.name] = "ok"
            except Exception as exc:
                logger.error(
                    "pipeline.step_failed",
                    step=step.name,
                    analysis_id=str(analysis.id),
                    error=str(exc),
                )
                statuses[step.name] = f"failed: {exc}"
            durations[step.name] = round(time.perf_counter() - started, 3)
            if on_step_completed is not None:
                try:
                    await on_step_completed(analysis, step.name)
                except Exception as exc:
                    logger.warning("pipeline.checkpoint_failed", step=step.name, error=str(exc))
        return analysis
