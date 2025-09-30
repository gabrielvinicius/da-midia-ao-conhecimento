# src/topic_modeling/infrastructure/sklearn_topic_modeling_service.py
import structlog
from typing import List
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import LatentDirichletAllocation

from .interfaces import ITopicModelingService
from .dependencies import register_topic_modeling

logger = structlog.get_logger(__name__)

@register_topic_modeling("sklearn_lda")
class SklearnTopicModelingService(ITopicModelingService):
    """Implementation of topic modeling using Scikit-learn's LDA."""

    def __init__(self):
        logger.info("topic_modeling.service.init", provider="sklearn_lda")
        self.vectorizer = TfidfVectorizer(stop_words='english', max_df=0.95, min_df=2)
        self.lda = LatentDirichletAllocation(n_components=10, random_state=0)

    @property
    def provider_name(self) -> str:
        return "sklearn_lda"

    def extract_topics(self, text: str, num_topics: int = 5, num_words: int = 5) -> List[str]:
        """Extracts topics from a block of text using LDA."""
        if not text or not text.strip():
            return []

        try:
            docs = [text]
            X = self.vectorizer.fit_transform(docs)
            
            self.lda.n_components = num_topics
            self.lda.fit(X)
            
            feature_names = self.vectorizer.get_feature_names_out()
            topics = []
            for topic_idx, topic in enumerate(self.lda.components_):
                top_words = [feature_names[i] for i in topic.argsort()[:-num_words - 1:-1]]
                topics.append(f"Topic #{topic_idx+1}: {', '.join(top_words)}")
            
            return topics
        except Exception as e:
            logger.error("topic_modeling.process.failed", error=str(e))
            return ["Error during topic modeling."]
