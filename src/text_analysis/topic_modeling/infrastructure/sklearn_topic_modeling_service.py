# src/topic_modeling/infrastructure/sklearn_topic_modeling_service.py
from typing import List

import structlog
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import TfidfVectorizer

from .dependencies import register_topic_modeling
from .interfaces import ITopicModelingService

logger = structlog.get_logger(__name__)

@register_topic_modeling("sklearn_lda")
class SklearnTopicModelingService(ITopicModelingService):
    """Implementation of topic modeling using Scikit-learn's LDA."""

    def __init__(self):
        logger.info("topic_modeling.service.init", provider="sklearn_lda")
        # Model is now created on-demand in the method

    @property
    def provider_name(self) -> str:
        return "sklearn_lda"

    def extract_topics(self, text: str, language: str = "english", num_topics: int = 5, num_words: int = 5) -> List[str]:
        """Extracts topics from a block of text using LDA, supporting multiple languages for stop words."""
        if not text or not text.strip():
            return []

        try:
            # Use the provided language for stop words. Fallback to english if unsupported.
            supported_languages = ['english', 'french', 'spanish'] # Add more as needed
            lang_to_use = language if language in supported_languages else 'english'

            vectorizer = TfidfVectorizer(stop_words=lang_to_use, max_df=0.95, min_df=2)
            lda = LatentDirichletAllocation(n_components=num_topics, random_state=0)

            docs = [text]
            X = vectorizer.fit_transform(docs)

            lda.fit(X)

            feature_names = vectorizer.get_feature_names_out()
            topics = []
            for topic_idx, topic in enumerate(lda.components_):
                top_words = [feature_names[i] for i in topic.argsort()[:-num_words - 1:-1]]
                topics.append(f"Topic #{topic_idx+1}: {', '.join(top_words)}")

            return topics
        except Exception as e:
            logger.error("topic_modeling.process.failed", extra={"error": str(e)})
            return ["Error during topic modeling."]
