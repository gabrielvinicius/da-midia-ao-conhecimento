"""Scripts usados para produzir os números da avaliação do TCC."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "scripts" / "evaluation"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wer_mod = _load("wer")
export_mod = _load("export_timings")


def test_wer_counts_each_error_type():
    sub = wer_mod.wer("a derivada mede a taxa", "a derivada medi a taxa")
    rem = wer_mod.wer("a derivada mede a taxa", "a derivada mede taxa")
    ins = wer_mod.wer("a derivada mede a taxa", "a derivada mede a taxa hoje")
    assert (sub["substitutions"], sub["deletions"], sub["insertions"]) == (1, 0, 0)
    assert (rem["substitutions"], rem["deletions"], rem["insertions"]) == (0, 1, 0)
    assert (ins["substitutions"], ins["deletions"], ins["insertions"]) == (0, 0, 1)
    assert sub["wer"] == pytest.approx(1 / 5)


def test_wer_total_counts_every_edit():
    # pontuação e maiúsculas não contam; 3 edições sobre 5 palavras
    r = wer_mod.wer("a derivada mede a taxa", "A derivada, medi taxa função!")
    assert r["wer"] == pytest.approx(3 / 5)


def test_wer_is_zero_for_identical_text_after_normalization():
    assert wer_mod.wer("Olá, mundo.", "olá mundo")["wer"] == 0


def test_latex_rows_follow_pipeline_order_and_brazilian_decimals():
    summary = [
        {"task_type": "analysis.synthesis", "runs": 2, "failures": 0, "avg_seconds": 40.25,
         "median_seconds": 40.25, "max_seconds": 41.0, "realtime_factor": None},
        {"task_type": "transcription", "runs": 2, "failures": 1, "avg_seconds": 12.5,
         "median_seconds": 12.5, "max_seconds": 12.5, "realtime_factor": 0.208},
    ]
    rows = export_mod.latex_rows(summary)
    assert rows[0].startswith("Transcrição & 2 & 1 & 12{,}5")
    assert "0{,}21" in rows[0]
    assert rows[1].startswith("Resumo final") and "-- \\\\" in rows[1]


def test_vram_peak_reads_nvidia_smi_csv(tmp_path):
    csv = tmp_path / "vram.csv"
    csv.write_text(
        "timestamp, memory.used [MiB]\n"
        "2026/09/30 10:00:00.000, 3120 MiB\n"
        "2026/09/30 10:00:01.000, 10412 MiB\n"
        "2026/09/30 10:00:02.000, 7001 MiB\n"
    )
    assert export_mod.vram_peak_mib(csv) == 10412
