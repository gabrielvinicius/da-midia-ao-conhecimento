from __future__ import annotations

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.shared.infrastructure.persistence.processing_stats_model import ProcessingStatModel

class ProcessingStatsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_stat(
        self,
        task_type: str,
        processing_duration: float,
        input_size_bytes: int | None = None,
        input_duration: float | None = None,
        model_name: str | None = None
    ) -> None:
        """Registra uma execução bem-sucedida."""
        stat = ProcessingStatModel(
            task_type=task_type,
            processing_duration_seconds=processing_duration,
            input_size_bytes=input_size_bytes,
            input_duration_seconds=input_duration,
            model_name=model_name
        )
        self.session.add(stat)
        await self.session.commit()

    async def get_avg_processing_speed(self, task_type: str, limit: int = 100) -> float | None:
        """
        Calcula a velocidade média (Bytes / Segundo) baseada nas últimas N execuções.
        Retorna None se não houver dados suficientes.
        """
        # Query: Pegar os últimos 100 registros onde size e duration > 0
        stmt = (
            select(ProcessingStatModel)
            .where(ProcessingStatModel.task_type == task_type)
            .where(ProcessingStatModel.input_size_bytes > 0)
            .where(ProcessingStatModel.processing_duration_seconds > 0)
            .order_by(ProcessingStatModel.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        stats = result.scalars().all()

        if not stats:
            return None

        total_bytes = sum(s.input_size_bytes for s in stats)
        total_seconds = sum(s.processing_duration_seconds for s in stats)

        if total_seconds == 0:
            return None

        # Retorna Bytes por Segundo
        return total_bytes / total_seconds

    async def get_avg_speed_ratio(self, task_type: str, limit: int = 100) -> float | None:
        """
        Calcula o fator de velocidade (Input Duration / Processing Time).
        Ex: 10.0 significa que processa 1h de áudio em 6 min.
        """
        stmt = (
            select(ProcessingStatModel)
            .where(ProcessingStatModel.task_type == task_type)
            .where(ProcessingStatModel.input_duration_seconds > 0)
            .where(ProcessingStatModel.processing_duration_seconds > 0)
            .order_by(ProcessingStatModel.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        stats = result.scalars().all()

        if not stats:
            return None

        total_input_duration = sum(s.input_duration_seconds for s in stats)
        total_proc_time = sum(s.processing_duration_seconds for s in stats)

        if total_proc_time == 0:
            return None

        return total_input_duration / total_proc_time
