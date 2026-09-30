"""Exporta os tempos de processamento gravados, prontos para o TCC.

Lê a tabela processing_stats (variável DATABASE_URL), agrupa por etapa e
modelo como a página de análises do administrador e imprime as linhas de uma
tabela LaTeX. Com --vram, lê também o registro do nvidia-smi gravado durante
o processamento e informa o pico de memória da GPU.

Uso:
    python scripts/evaluation/export_timings.py [--days 7] [--vram vram.csv]

Para registrar a memória da GPU enquanto as mídias são processadas:
    nvidia-smi --query-gpu=timestamp,memory.used --format=csv -l 1 > vram.csv
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path

TASK_LABELS = {
    "transcription": "Transcrição",
    "text_analysis": "Análise completa",
    "analysis.chunking": "Divisão em trechos",
    "analysis.sentiment": "Sentimento",
    "analysis.topic_modeling": "Temas",
    "analysis.topic_titles": "Títulos dos temas",
    "analysis.knowledge_indexing": "Indexação semântica",
    "analysis.visual_insight": "Análise visual",
    "analysis.summarization": "Resumo por tema",
    "analysis.synthesis": "Resumo final",
}


def _num(value, fmt="{:.1f}") -> str:
    return "--" if value is None else fmt.format(value).replace(".", "{,}")


def latex_rows(summary: list[dict]) -> list[str]:
    order = list(TASK_LABELS)
    summary = sorted(summary, key=lambda s: order.index(s["task_type"]) if s["task_type"] in order else 99)
    rows = []
    for s in summary:
        label = TASK_LABELS.get(s["task_type"], s["task_type"]).replace("_", r"\_")
        rows.append(
            f"{label} & {s['runs']} & {s['failures']} & {_num(s['avg_seconds'])} & "
            f"{_num(s['median_seconds'])} & {_num(s['max_seconds'])} & "
            f"{_num(s['realtime_factor'], '{:.2f}')} \\\\"
        )
    return rows


def vram_peak_mib(path: Path) -> int:
    """Maior valor de memory.used (MiB) num CSV do nvidia-smi."""
    peak = 0
    with path.open(encoding="utf-8") as fh:
        for row in csv.reader(fh):
            for cell in row:
                cell = cell.strip()
                if cell.endswith("MiB") and cell[:-3].strip().isdigit():
                    peak = max(peak, int(cell[:-3]))
    return peak


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--days", type=int, help="considera só os últimos N dias")
    parser.add_argument("--vram", type=Path, help="CSV gerado pelo nvidia-smi")
    args = parser.parse_args()

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from src.shared.infrastructure.config.settings import settings
    from src.shared.infrastructure.persistence.processing_stats_model import ProcessingStatModel
    from src.shared.infrastructure.repositories.processing_stats_repository import summarize_rows

    stmt = select(ProcessingStatModel)
    if args.days:
        stmt = stmt.where(ProcessingStatModel.created_at >= datetime.utcnow() - timedelta(days=args.days))
    with Session(create_engine(settings.sync_database_url)) as session:
        rows = session.execute(stmt).scalars().all()

    if not rows:
        print("Nenhuma execução registrada. Processe as mídias do conjunto de avaliação primeiro.")
        return
    print("% Etapa & Execuções & Falhas & Média (s) & Mediana (s) & Máximo (s) & Tempo real")
    for line in latex_rows(summarize_rows(rows)):
        print(line)
    if args.vram:
        peak = vram_peak_mib(args.vram)
        print(f"% Pico de memória da GPU: {peak} MiB ({peak / 1024:.1f} GiB)")


if __name__ == "__main__":
    main()
