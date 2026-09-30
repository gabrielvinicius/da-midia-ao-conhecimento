"""Taxa de erro de palavras (WER) de uma transcrição.

Compara a transcrição gerada com uma referência digitada à mão. Ambas são
normalizadas (minúsculas, sem pontuação), e o WER é
(substituições + remoções + inserções) / palavras da referência.

Uso:
    python scripts/evaluation/wer.py referencia.txt transcricao.txt
    python scripts/evaluation/wer.py referencia.txt --media-id <uuid>

Com --media-id, a transcrição é lida do banco (variável DATABASE_URL).
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path


def normalize(text: str) -> list[str]:
    text = unicodedata.normalize("NFC", text.lower())
    text = re.sub(r"[^\w\s]", " ", text)
    return text.split()


def word_errors(reference: list[str], hypothesis: list[str]) -> tuple[int, int, int]:
    """(substituições, remoções, inserções) pelo alinhamento de Levenshtein."""
    rows, cols = len(reference) + 1, len(hypothesis) + 1
    # cada célula guarda (custo, subst, remoções, inserções)
    prev = [(j, 0, 0, j) for j in range(cols)]
    for i in range(1, rows):
        cur = [(i, 0, i, 0)]
        for j in range(1, cols):
            if reference[i - 1] == hypothesis[j - 1]:
                cur.append(prev[j - 1])
                continue
            sub, rem, ins = prev[j - 1], prev[j], cur[j - 1]
            best = min(sub, rem, ins, key=lambda c: c[0])
            if best is sub:
                cur.append((sub[0] + 1, sub[1] + 1, sub[2], sub[3]))
            elif best is rem:
                cur.append((rem[0] + 1, rem[1], rem[2] + 1, rem[3]))
            else:
                cur.append((ins[0] + 1, ins[1], ins[2], ins[3] + 1))
        prev = cur
    _, s, d, n = prev[-1]
    return s, d, n


def wer(reference: str, hypothesis: str) -> dict:
    ref, hyp = normalize(reference), normalize(hypothesis)
    s, d, i = word_errors(ref, hyp)
    return {
        "reference_words": len(ref),
        "substitutions": s,
        "deletions": d,
        "insertions": i,
        "wer": (s + d + i) / len(ref) if ref else 0.0,
    }


def _transcription_from_db(media_id: str) -> str:
    from sqlalchemy import create_engine, text

    from src.shared.infrastructure.config.settings import settings

    engine = create_engine(settings.sync_database_url)
    with engine.connect() as conn:
        content = conn.execute(
            text("SELECT content FROM transcriptions WHERE media_id = :id"),
            {"id": media_id},
        ).scalar()
    if content is None:
        sys.exit(f"Nenhuma transcrição encontrada para a mídia {media_id}.")
    return content


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("reference", type=Path, help="arquivo .txt com a transcrição de referência")
    parser.add_argument("hypothesis", type=Path, nargs="?", help="arquivo .txt com a transcrição gerada")
    parser.add_argument("--media-id", help="lê a transcrição gerada do banco")
    args = parser.parse_args()

    if bool(args.hypothesis) == bool(args.media_id):
        parser.error("informe o arquivo da transcrição gerada ou --media-id (um dos dois)")
    hypothesis = (
        _transcription_from_db(args.media_id)
        if args.media_id
        else args.hypothesis.read_text(encoding="utf-8")
    )
    r = wer(args.reference.read_text(encoding="utf-8"), hypothesis)
    print(
        f"WER: {r['wer']:.2%}  (referência: {r['reference_words']} palavras; "
        f"substituições: {r['substitutions']}, remoções: {r['deletions']}, "
        f"inserções: {r['insertions']})"
    )


if __name__ == "__main__":
    main()
