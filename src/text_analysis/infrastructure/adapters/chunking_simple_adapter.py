"""Chunking implementation using simple heuristics."""

from __future__ import annotations

import re
from uuid import uuid4

from src.text_analysis.application.ports.chunking import ChunkingServicePort
from src.text_analysis.domain import Document, TextChunk


class SimpleChunker(ChunkingServicePort):
    def chunk(self, document: Document, size: int, overlap: int) -> list[TextChunk]:
        if document.segments:
            return self._chunk_segments(document.segments, size)

        # Texto sem horários (documento, OCR): os trechos não têm posição na
        # gravação, então start/end ficam vazios. Antes, start recebia a posição
        # em caracteres, e a busca mostrava um "momento" falso para PDFs.
        text = document.text.strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s for s in sentences if s.strip()]

        if not sentences:
            return [TextChunk(id=str(uuid4()), text=text)]

        chunks: list[TextChunk] = []
        buffer: list[str] = []
        current_len = 0

        for sentence in sentences:
            if current_len + len(sentence) > size and buffer:
                chunk_text = " ".join(buffer).strip()
                chunks.append(TextChunk(id=str(uuid4()), text=chunk_text))
                # overlap: keep tail of buffer
                tail = " ".join(chunk_text.split()[-overlap // 5 :]) if overlap else ""
                buffer = [tail] if tail else []
                current_len = len(tail)
            buffer.append(sentence)
            current_len += len(sentence)

        if buffer:
            chunk_text = " ".join(buffer).strip()
            chunks.append(TextChunk(id=str(uuid4()), text=chunk_text))

        return chunks

    @staticmethod
    def _chunk_segments(segments: list, size: int) -> list[TextChunk]:
        """Agrupa segmentos consecutivos da transcrição até ~size caracteres.

        Cada segmento do Whisper costuma ter só uma frase curta; agrupá-los dá
        trechos com contexto suficiente para busca e sentimento, preservando o
        início do primeiro segmento e o fim do último.
        """
        chunks: list[TextChunk] = []
        buffer: list[str] = []
        start = end = None

        def flush() -> None:
            if buffer:
                chunks.append(
                    TextChunk(id=str(uuid4()), text=" ".join(buffer), start=start, end=end)
                )

        for segment in segments:
            if not isinstance(segment, dict):
                continue
            text = (segment.get("text") or "").strip()
            if not text:
                continue
            if buffer and sum(len(t) + 1 for t in buffer) + len(text) > size:
                flush()
                buffer, start = [], None
            if start is None:
                start = segment.get("start")
            end = segment.get("end")
            buffer.append(text)
        flush()
        return chunks
