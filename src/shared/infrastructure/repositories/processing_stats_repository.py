from __future__ import annotations

from datetime import datetime, timedelta
from statistics import mean, median

from sqlalchemy import select
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
        model_name: str | None = None,
        status: str = "success",
    ) -> None:
        """Registra uma execução (bem-sucedida ou não)."""
        stat = ProcessingStatModel(
            task_type=task_type,
            processing_duration_seconds=processing_duration,
            input_size_bytes=input_size_bytes,
            input_duration_seconds=input_duration,
            model_name=model_name,
            status=status,
        )
        self.session.add(stat)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def summarize(self, days: int | None = None) -> list[dict]:
        """Resume as durações por tipo de tarefa e modelo.

        Para cada grupo: execuções, falhas, média, mediana e máximo (em
        segundos) e, quando a duração da mídia é conhecida, o fator de tempo
        real (tempo de processamento / duração da mídia; 0,5 = metade do tempo
        da gravação).
        """
        stmt = select(ProcessingStatModel)
        if days:
            since = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(ProcessingStatModel.created_at >= since)
        rows = (await self.session.execute(stmt)).scalars().all()
        return summarize_rows(rows)

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


def summarize_rows(rows) -> list[dict]:
    """Agrupa as execuções por tarefa e modelo e calcula as estatísticas."""
    groups: dict = {}
    for row in rows:
        groups.setdefault((row.task_type, row.model_name), []).append(row)

    summary = []
    for (task_type, model_name), items in sorted(groups.items(), key=lambda kv: (kv[0][0], kv[0][1] or "")):
        ok = [i for i in items if (i.status or "success") == "success"]
        durations = [i.processing_duration_seconds for i in ok]
        with_media = [i for i in ok if (i.input_duration_seconds or 0) > 0]
        media_total = sum(i.input_duration_seconds for i in with_media)
        summary.append({
            "task_type": task_type,
            "model_name": model_name,
            "runs": len(items),
            "failures": len(items) - len(ok),
            "avg_seconds": round(mean(durations), 2) if durations else None,
            "median_seconds": round(median(durations), 2) if durations else None,
            "max_seconds": round(max(durations), 2) if durations else None,
            "realtime_factor": (
                round(sum(i.processing_duration_seconds for i in with_media) / media_total, 3)
                if media_total
                else None
            ),
        })
    return summary
