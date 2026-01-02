"""BERTopic adapter with fallback heuristic."""

from __future__ import annotations

from collections import Counter

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.shared.infrastructure.config.settings import settings
from src.text_analysis.application.ports.topic_modeling import TopicModelingPort
from src.text_analysis.domain import TextChunk, Topic

logger = get_logger(__name__)


class BERTopicAdapter(TopicModelingPort):
    def __init__(
        self,
        model_name: str,
        use_transformer_representation: bool = False,
        transformer_model_name: str | None = None,
        device: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.use_transformer_representation = use_transformer_representation
        self.transformer_model_name = transformer_model_name
        self.device = device or settings.resolved_device
        self._model = None
        self._initialized = False

    def _get_model(self):
        if not self._initialized:
            try:  # pragma: no cover
                from bertopic import BERTopic

                representation_model = None
                if self.use_transformer_representation:
                    try:
                        from bertopic.representation import TextGeneration
                        from transformers import pipeline

                        # Map 'cpu' or device ID
                        device_idx = -1 if self.device == "cpu" else 0

                        generator = pipeline(
                            "text2text-generation",
                            model=self.transformer_model_name or "google/flan-t5-base",
                            device=device_idx
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
            self._initialized = True
        return self._model

    def model_topics(
        self, chunks: list[TextChunk], embeddings: list[list[float]], language: str
    ) -> tuple[list[Topic], dict]:
        model = self._get_model()
        if model and embeddings:
            try:
                import numpy as np  # lazy import to avoid hard dep at import time

                docs = [chunk.text for chunk in chunks]
                np_embeddings = (
                    embeddings
                    if hasattr(embeddings, "shape")
                    else np.array(embeddings, dtype="float32")
                )
                topics, probs = model.fit_transform(docs, np_embeddings)
                info = model.get_topic_info()
                topics_out: list[Topic] = []
                for topic_id in set(topics):
                    words = [term for term, _ in model.get_topic(topic_id) or []]
                    snippets = [
                        chunk.text for chunk, t in zip(chunks, topics) if t == topic_id
                    ]
                    topics_out.append(
                        Topic(
                            id=int(topic_id),
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

    def _fallback(self, chunks: list[TextChunk]) -> tuple[list[Topic], dict]:
        text_all = " ".join(chunk.text for chunk in chunks)
        tokens = [t.lower() for t in text_all.split() if len(t) > 3]
        common = [word for word, _ in Counter(tokens).most_common(10)]
        topic = Topic(
            id=0,
            keywords=common or ["geral"],
            snippets=[chunk.text for chunk in chunks[:3]],
            title=common[0] if common else "Geral",
            size=len(chunks),
            diagnostics={"method": "fallback"},
        )
        return [topic], {"method": "fallback"}
