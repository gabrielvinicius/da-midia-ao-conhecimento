"""BERTopic adapter with fallback heuristic."""

from __future__ import annotations

import logging
from collections import Counter
from typing import List, Tuple

from src.text_analysis.application.ports.topic_modeling import TopicModelingPort
from src.text_analysis.domain import TextChunk, Topic

logger = logging.getLogger(__name__)


class BERTopicAdapter(TopicModelingPort):
    def __init__(
        self,
        model_name: str,
        use_transformer_representation: bool = False,
        transformer_model_name: str | None = None,
    ) -> None:
        self.model_name = model_name
        self._model = None
        try:  # pragma: no cover - optional dependency
            from bertopic import BERTopic

            representation_model = None
            if use_transformer_representation:
                try:
                    from bertopic.representation import TextGeneration
                    from transformers import pipeline

                    generator = pipeline(
                        "text2text-generation",
                        model=transformer_model_name or "google/flan-t5-base",
                    )
                    representation_model = TextGeneration(generator)
                    logger.info(
                        "Using transformer TextGeneration for topic titles."
                    )
                except Exception as rep_exc:  # pragma: no cover
                    logger.warning(
                        "Transformer TextGeneration unavailable (%s). "
                        "Falling back to default BERTopic.",
                        rep_exc,
                    )

            self._model = BERTopic(representation_model=representation_model)
        except Exception as exc:
            logger.warning(
                "BERTopic unavailable (%s). Using simple keywords fallback.", exc
            )

    def model_topics(
        self, chunks: List[TextChunk], embeddings: List[list[float]], language: str
    ) -> Tuple[List[Topic], dict]:
        if self._model:
            try:
                docs = [chunk.text for chunk in chunks]
                topics, probs = self._model.fit_transform(docs, embeddings)
                info = self._model.get_topic_info()
                topics_out: List[Topic] = []
                for topic_id in set(topics):
                    words = [term for term, _ in self._model.get_topic(topic_id) or []]
                    snippets = [
                        chunk.text for chunk, t in zip(chunks, topics) if t == topic_id
                    ]
                    topics_out.append(
                        Topic(
                            topic_id=int(topic_id),
                            keywords=words[:10],
                            snippets=snippets[:5],
                            title=words[0] if words else None,
                            size=len(snippets),
                            diagnostics={"probabilities": probs},
                        )
                    )
                diagnostics = {
                    "topics": info.to_dict() if hasattr(info, "to_dict") else {}
                }
                return topics_out, diagnostics
            except Exception as exc:  # pragma: no cover
                logger.error("BERTopic run failed: %s", exc)
        return self._fallback(chunks)

    def _fallback(self, chunks: List[TextChunk]) -> Tuple[List[Topic], dict]:
        text_all = " ".join(chunk.text for chunk in chunks)
        tokens = [t.lower() for t in text_all.split() if len(t) > 3]
        common = [word for word, _ in Counter(tokens).most_common(10)]
        topic = Topic(
            topic_id=0,
            keywords=common or ["geral"],
            snippets=[chunk.text for chunk in chunks[:3]],
            title=common[0] if common else "Geral",
            size=len(chunks),
            diagnostics={"method": "fallback"},
        )
        return [topic], {"method": "fallback"}
