"""Topic modeling simples via TF-IDF + k-means (fallback leve)."""

from __future__ import annotations

from src.shared.infrastructure.observability.logging.logging_config import get_logger
from src.text_analysis.application.ports.topic_modeling import TopicModelingPort
from src.text_analysis.domain import Topic, TextChunk
from src.text_analysis.infrastructure.adapters.stopwords import stop_words_for

logger = get_logger(__name__)


class TFIDFTopicModelingAdapter(TopicModelingPort):
    """Fallback rápido para ambientes sem BERTopic/transformers."""

    def __init__(self, n_topics: int = 5, max_features: int = 5000, random_state: int = 42) -> None:
        self.n_topics = n_topics
        self.max_features = max_features
        self.random_state = random_state
        self.n_init = 10

    async def model_topics(
        self, chunks: list[TextChunk], embeddings: list[list[float]], language: str
    ) -> tuple[list[Topic], dict]:
        try:  # Lazy imports para evitar falhas em ambientes sem sklearn/numpy
            import numpy as np  # type: ignore
            from sklearn.cluster import KMeans  # type: ignore
            from sklearn.feature_extraction.text import TfidfVectorizer  # type: ignore
        except Exception as exc:  # pragma: no cover
            logger.warning("tfidf_topic_modeling.unavailable", error=str(exc))
            return [], {"error": "sklearn/numpy indisponível"}

        texts = [c.text for c in chunks]
        if not texts:
            return [], {}

        try:
            # O scikit-learn só aceita "english" como nome de lista; para os
            # demais idiomas passamos a lista explicitamente.
            stop_words = stop_words_for(language)
            if stop_words is None and language:
                logger.info("tfidf.stopwords.unsupported_language", language=language)
            vectorizer = TfidfVectorizer(max_features=self.max_features, stop_words=stop_words)
            X = vectorizer.fit_transform(texts)
            k = min(self.n_topics, X.shape[0])
            if k == 0:
                return [], {}
            km = KMeans(n_clusters=k, random_state=self.random_state, n_init=self.n_init)
            labels = km.fit_predict(X)
            centroids = km.cluster_centers_
            feature_names = vectorizer.get_feature_names_out()

            topics: list[Topic] = []
            for idx in range(k):
                mask = labels == idx
                indices = np.where(mask)[0]
                top_terms_idx = centroids[idx].argsort()[::-1][:8]
                keywords = [feature_names[i] for i in top_terms_idx]
                topic_chunks = [chunks[i] for i in indices]
                topics.append(
                    Topic(
                        id=idx + 1,
                        title=f"Tópico {idx+1}",
                        keywords=keywords,
                        snippets=[c.text for c in topic_chunks],
                        summary="; ".join(keywords[:3]) or "Não informado",
                        diagnostics={"size": len(indices)},
                    )
                )
            diagnostics = {"method": "tfidf-kmeans", "k": k}
            return topics, diagnostics
        except Exception as exc:  # pragma: no cover
            logger.warning("tfidf_topic_modeling.failed", error=str(exc))
            return [], {"error": str(exc)}


__all__ = ["TFIDFTopicModelingAdapter"]
