"""Chunking service port to split documents."""

from __future__ import annotations

from typing import List

from abc import ABC, abstractmethod

from ...domain import Document, TextChunk


class ChunkingServicePort(ABC):
    @abstractmethod
    def chunk(self, document: Document, size: int, overlap: int) -> List[TextChunk]:
        """Produce textual chunks respecting overlap and order."""

