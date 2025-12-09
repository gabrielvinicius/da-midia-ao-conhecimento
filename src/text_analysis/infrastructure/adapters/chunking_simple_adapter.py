"""Chunking implementation using simple heuristics."""

from __future__ import annotations

import re
from typing import List
from uuid import uuid4

from src.text_analysis.application.ports.chunking import ChunkingServicePort
from src.text_analysis.domain.entities import Document
from src.text_analysis.domain.value_objects import TextChunk


class SimpleChunker(ChunkingServicePort):
    def chunk(self, document: Document, size: int, overlap: int) -> List[TextChunk]:
        if document.segments:
            return [
                TextChunk(
                    id=str(uuid4()),
                    text=segment["text"],
                    start=segment.get("start"),
                    end=segment.get("end"),
                )
                for segment in document.segments
                if isinstance(segment, dict) and segment.get("text")
            ]

        text = document.text.strip()
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s for s in sentences if s.strip()]

        if not sentences:
            return [TextChunk(id=str(uuid4()), text=text, start=0.0)]

        chunks: List[TextChunk] = []
        buffer: list[str] = []
        current_len = 0
        start = 0.0

        for sentence in sentences:
            if current_len + len(sentence) > size and buffer:
                chunk_text = " ".join(buffer).strip()
                chunks.append(TextChunk(id=str(uuid4()), text=chunk_text, start=start))
                # overlap: keep tail of buffer
                tail = " ".join(chunk_text.split()[-overlap // 5 :]) if overlap else ""
                buffer = [tail] if tail else []
                current_len = len(tail)
                start += len(chunk_text) - overlap if overlap < len(chunk_text) else 0
            buffer.append(sentence)
            current_len += len(sentence)

        if buffer:
            chunk_text = " ".join(buffer).strip()
            chunks.append(TextChunk(id=str(uuid4()), text=chunk_text, start=start))

        return chunks
