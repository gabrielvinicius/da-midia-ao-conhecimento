"""Concrete implementation of ITextProcessor for text processing operations.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class TextProcessor:
    """Processes raw text applying deterministic enrichment steps."""

    def __init__(self) -> None:
        self._processors = {
            "normalize": self._build_normalized_payload,
            "analyze": self._build_analysis_payload,
            "chunks": self._build_chunk_payload,
            "keywords": self._build_keyword_payload,
        }

    async def process_text(
        self,
        text_content: str,
        processing_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Async shim used by Celery tasks when an event loop already exists."""

        return self.process_text_sync(text_content, processing_type, options)

    def process_text_sync(
        self,
        text_content: str,
        processing_type: str,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        options = options or {}
        normalized_text = self._normalize_text(text_content)
        key = (processing_type or "analyze").strip().lower() or "analyze"
        handler = self._processors.get(key, self._processors["analyze"])

        logger.info(
            "text_processor.processing_text_sync",
            processing_type=key,
            text_length=len(normalized_text),
            options=options,
        )

        payload = handler(normalized_text, options)
        stats = self._compute_stats(normalized_text)

        result = {
            "processing_type": key,
            "normalized_text": normalized_text,
            "stats": stats,
            **payload,
        }

        logger.info("text_processor.text_processed_sync", summary={"processing_type": key, "word_count": stats["word_count"]})
        return result

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _build_normalized_payload(self, text: str, _: Dict[str, Any]) -> Dict[str, Any]:
        return {"message": "Texto normalizado"}

    def _build_analysis_payload(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        sentences = self._split_sentences(text)
        paragraphs = [paragraph for paragraph in (p.strip() for p in text.split("\n\n")) if paragraph]
        return {
            "insights": {
                "sentences_sample": sentences[: min(3, len(sentences))],
                "paragraph_count": len(paragraphs),
            }
        }

    def _build_chunk_payload(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        chunk_size = max(200, int(options.get("chunk_size", 1200)))
        overlap = max(0, int(options.get("overlap", 32)))
        chunks: List[Dict[str, Any]] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunks.append({
                    "index": len(chunks),
                    "start": start,
                    "end": end,
                    "length": len(chunk_text),
                    "text": chunk_text,
                })
            start = end - overlap if overlap else end
            if start < 0:
                start = 0
        return {"chunks": chunks, "chunk_size": chunk_size, "overlap": overlap}

    def _build_keyword_payload(self, text: str, options: Dict[str, Any]) -> Dict[str, Any]:
        limit = max(3, int(options.get("limit", 10)))
        tokens = self._tokenize(text)
        stop_words = self._stop_words()
        filtered = [token for token in tokens if token not in stop_words and len(token) > 2]
        counter = Counter(filtered)
        top_keywords = counter.most_common(limit)
        total = sum(counter.values()) or 1
        keywords = [
            {
                "term": term,
                "count": count,
                "score": round(count / total, 4),
            }
            for term, count in top_keywords
        ]
        return {"keywords": keywords, "total_keywords": len(filtered)}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalize_text(self, text: str) -> str:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[\t ]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    def _compute_stats(self, text: str) -> Dict[str, Any]:
        tokens = self._tokenize(text)
        sentences = self._split_sentences(text)
        paragraphs = [p for p in text.split("\n\n") if p.strip()]
        chars = len(text)
        words_per_minute = max(120, min(250, int(tokens and len(tokens) * 2) or 200))
        estimated_minutes = len(tokens) / words_per_minute if tokens else 0
        return {
            "word_count": len(tokens),
            "sentence_count": len(sentences),
            "paragraph_count": len(paragraphs),
            "character_count": chars,
            "estimated_read_time_seconds": int(math.ceil(estimated_minutes * 60)),
        }

    def _split_sentences(self, text: str) -> List[str]:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+", text.lower())

    @staticmethod
    def _stop_words() -> set[str]:
        return {
            "a", "ao", "aos", "as", "de", "da", "das", "do", "dos", "e", "em", "no", "na",
            "nas", "nos", "o", "os", "para", "por", "que", "se", "um", "uma", "com", "não",
            "and", "the", "is", "are", "this", "that", "was", "were", "be", "to", "of", "in",
        }


__all__ = ["TextProcessor"]
