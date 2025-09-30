# src/sentiment_analysis/infrastructure/sklearn_topic_modeling_service.py
from sklearn.feature_extraction.text import TfidfVectorizer
from typing import List
import structlog

from .interfaces import ITopicModelingService

logger = structlog.get_logger(__name__)

class SklearnTopicModelingService(ITopicModelingService):
    """Implementation of the topic modeling service using scikit-learn's TfidfVectorizer."""

    def __init__(self):
        logger.info("topic_modeling.service.init", model="TfidfVectorizer")
        # Initialize the vectorizer with common English stop words
        self.vectorizer = TfidfVectorizer(stop_words='english', max_features=100)

    def extract_topics(self, text: str, num_topics: int = 10) -> List[str]:
        """Extracts keywords using TF-IDF."""
        if not text or not text.strip():
            return []

        try:
            # Fit and transform the text. We treat the whole text as a single document.
            tfidf_matrix = self.vectorizer.fit_transform([text])
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Get the scores for the single document
            scores = tfidf_matrix.toarray().flatten()
            
            # Get indices of top scores
            top_indices = scores.argsort()[-num_topics:][::-1]
            
            top_keywords = [feature_names[i] for i in top_indices]
            
            logger.info("topic_modeling.process.completed", num_topics=len(top_keywords))
            return top_keywords

        except Exception as e:
            logger.error("topic_modeling.process.failed", error=str(e))
            return []
