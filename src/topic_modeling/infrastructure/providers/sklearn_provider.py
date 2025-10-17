# src/topic_modeling/infrastructure/providers/sklearn_provider.py
"""
Scikit-learn topic modeling provider - OCP and SRP compliance.
"""
import asyncio
from typing import Dict, Any, List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.decomposition import LatentDirichletAllocation, NMF
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from src.topic_modeling.domain.interfaces import TopicModelingConfiguration
from src.topic_modeling.infrastructure.providers.base_provider import (
    BaseTopicModelingProvider, 
    TopicModelingProviderError
)


class SklearnConfiguration(TopicModelingConfiguration):
    """Configuration for scikit-learn topic modeling - SRP compliance."""
    
    def __init__(
        self,
        algorithm: str = "lda",  # lda, nmf, kmeans
        max_text_length: int = 100000,
        max_features: int = 1000,
        min_df: int = 2,
        max_df: float = 0.95,
        ngram_range: tuple = (1, 1),
        random_state: int = 42
    ):
        self.algorithm = algorithm
        self.max_text_length = max_text_length
        self.max_features = max_features
        self.min_df = min_df
        self.max_df = max_df
        self.ngram_range = ngram_range
        self.random_state = random_state
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "algorithm": self.algorithm,
            "max_text_length": self.max_text_length,
            "max_features": self.max_features,
            "min_df": self.min_df,
            "max_df": self.max_df,
            "ngram_range": self.ngram_range,
            "random_state": self.random_state
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        valid_algorithms = ["lda", "nmf", "kmeans"]
        return (
            self.algorithm in valid_algorithms and
            self.max_text_length > 0 and
            self.max_features > 0 and
            self.min_df > 0 and
            0.0 < self.max_df <= 1.0
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        # Scikit-learn supports these languages for stop words
        return ["english", "arabic", "danish", "dutch", "finnish", "french", 
                "german", "hungarian", "italian", "norwegian", "portuguese", 
                "romanian", "russian", "spanish", "swedish"]
    
    def get_max_text_length(self) -> int:
        """Get maximum text length."""
        return self.max_text_length


class SklearnTopicModelingProvider(BaseTopicModelingProvider):
    """
    Scikit-learn topic modeling provider.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: SklearnConfiguration):
        super().__init__(config)
        self._config = config
        self._vectorizer = None
        self._model = None
    
    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return f"sklearn_{self._config.algorithm}"
    
    def _initialize_provider(self) -> None:
        """Initialize scikit-learn components."""
        try:
            # Initialize based on algorithm
            if self._config.algorithm == "lda":
                self._vectorizer = CountVectorizer(
                    max_features=self._config.max_features,
                    min_df=self._config.min_df,
                    max_df=self._config.max_df,
                    ngram_range=self._config.ngram_range,
                    stop_words=None  # Will be set per request
                )
            else:
                self._vectorizer = TfidfVectorizer(
                    max_features=self._config.max_features,
                    min_df=self._config.min_df,
                    max_df=self._config.max_df,
                    ngram_range=self._config.ngram_range,
                    stop_words=None  # Will be set per request
                )
                
        except Exception as e:
            raise TopicModelingProviderError(f"Failed to initialize sklearn provider: {e}") from e
    
    async def _do_extract_topics(
        self, 
        text: str, 
        language: str, 
        num_topics: int,
        num_words_per_topic: int
    ) -> List[Dict[str, Any]]:
        """Actual topic extraction implementation using scikit-learn."""
        try:
            # Set language-specific stop words
            stop_words = self._get_stop_words(language)
            
            # Create vectorizer with stop words
            vectorizer = self._create_vectorizer_for_language(stop_words)
            
            # Create model
            model = self._create_model(num_topics)
            
            # Vectorize text
            documents = self._split_text_into_documents(text)
            X = await asyncio.to_thread(vectorizer.fit_transform, documents)
            
            # Fit model
            await asyncio.to_thread(model.fit, X)
            
            # Extract topics
            feature_names = vectorizer.get_feature_names_out()
            topics = self._extract_topics_from_model(
                model, feature_names, num_topics, num_words_per_topic
            )
            
            return topics
            
        except Exception as e:
            raise TopicModelingProviderError(f"Sklearn topic extraction failed: {e}") from e
    
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        return self._config.get_supported_languages()
    
    def _supports_multilingual(self) -> bool:
        """Whether provider supports multilingual processing."""
        return True
    
    def _supports_dynamic_topics(self) -> bool:
        """Whether provider supports dynamic topic number detection."""
        return False  # Sklearn requires explicit number of topics
    
    def _supports_coherence_scoring(self) -> bool:
        """Whether provider supports coherence scoring."""
        return True
    
    def _create_vectorizer_for_language(self, stop_words):
        """Create vectorizer with language-specific stop words."""
        if self._config.algorithm == "lda":
            return CountVectorizer(
                max_features=self._config.max_features,
                min_df=self._config.min_df,
                max_df=self._config.max_df,
                ngram_range=self._config.ngram_range,
                stop_words=stop_words
            )
        else:
            return TfidfVectorizer(
                max_features=self._config.max_features,
                min_df=self._config.min_df,
                max_df=self._config.max_df,
                ngram_range=self._config.ngram_range,
                stop_words=stop_words
            )
    
    def _create_model(self, num_topics: int):
        """Create topic modeling model based on algorithm."""
        if self._config.algorithm == "lda":
            return LatentDirichletAllocation(
                n_components=num_topics,
                random_state=self._config.random_state,
                max_iter=10,
                learning_method='online'
            )
        elif self._config.algorithm == "nmf":
            return NMF(
                n_components=num_topics,
                random_state=self._config.random_state,
                max_iter=200
            )
        elif self._config.algorithm == "kmeans":
            return KMeans(
                n_clusters=num_topics,
                random_state=self._config.random_state,
                n_init=10
            )
        else:
            raise TopicModelingProviderError(f"Unknown algorithm: {self._config.algorithm}")
    
    def _split_text_into_documents(self, text: str) -> List[str]:
        """Split text into documents for better topic modeling."""
        # Split by paragraphs first
        paragraphs = text.split('\n\n')
        documents = []
        
        for paragraph in paragraphs:
            if paragraph.strip() and len(paragraph.strip()) > 50:  # Minimum paragraph length
                documents.append(paragraph.strip())
        
        # If we have too few documents, split by sentences
        if len(documents) < 3:
            import re
            sentences = re.split(r'[.!?]+', text)
            documents = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 20]
        
        # If still too few, use the whole text as one document
        if len(documents) < 2:
            documents = [text]
        
        return documents
    
    def _extract_topics_from_model(
        self, 
        model, 
        feature_names: np.ndarray, 
        num_topics: int,
        num_words_per_topic: int
    ) -> List[Dict[str, Any]]:
        """Extract topics from trained model."""
        topics = []
        
        if hasattr(model, 'components_'):  # LDA, NMF
            for topic_idx, topic in enumerate(model.components_):
                # Get top words for this topic
                top_indices = topic.argsort()[-num_words_per_topic:][::-1]
                top_words = [feature_names[i] for i in top_indices]
                top_scores = [topic[i] for i in top_indices]
                
                # Normalize scores
                normalized_scores = self._calculate_word_importance(top_scores)
                
                # Calculate coherence score
                coherence_score = self._calculate_topic_coherence(top_words, top_scores)
                
                topic_dict = {
                    "words": top_words,
                    "scores": normalized_scores,
                    "raw_scores": top_scores,
                    "coherence_score": coherence_score,
                    "dominant_words": top_words[:3]  # Top 3 words
                }
                
                topics.append(topic_dict)
        
        elif hasattr(model, 'cluster_centers_'):  # KMeans
            for topic_idx, center in enumerate(model.cluster_centers_):
                # Get top words for this cluster
                top_indices = center.argsort()[-num_words_per_topic:][::-1]
                top_words = [feature_names[i] for i in top_indices]
                top_scores = [center[i] for i in top_indices]
                
                # Normalize scores
                normalized_scores = self._calculate_word_importance(top_scores)
                
                # Calculate coherence score
                coherence_score = self._calculate_topic_coherence(top_words, top_scores)
                
                topic_dict = {
                    "words": top_words,
                    "scores": normalized_scores,
                    "raw_scores": top_scores,
                    "coherence_score": coherence_score,
                    "dominant_words": top_words[:3]
                }
                
                topics.append(topic_dict)
        
        return topics
    
    def _get_stop_words(self, language: str) -> str:
        """Get stop words for language."""
        # Map our language codes to sklearn stop words
        language_mapping = {
            "en": "english",
            "es": "spanish",
            "fr": "french",
            "de": "german",
            "it": "italian",
            "pt": "portuguese",
            "ru": "russian",
            "ar": "arabic",
            "da": "danish",
            "nl": "dutch",
            "fi": "finnish",
            "hu": "hungarian",
            "no": "norwegian",
            "ro": "romanian",
            "sv": "swedish"
        }
        
        sklearn_language = language_mapping.get(language, "english")
        
        # Check if language is supported by sklearn
        supported = self._config.get_supported_languages()
        if sklearn_language not in supported:
            sklearn_language = "english"
        
        return sklearn_language
    
    def _calculate_topic_coherence(self, words: List[str], scores: List[float]) -> float:
        """Calculate a simple coherence score for a topic."""
        if not words or not scores:
            return 0.0
        
        # Simple coherence based on score distribution
        # More even distribution = higher coherence
        if len(scores) < 2:
            return 0.5
        
        # Calculate coefficient of variation (lower = more coherent)
        mean_score = np.mean(scores)
        std_score = np.std(scores)
        
        if mean_score == 0:
            return 0.0
        
        cv = std_score / mean_score
        
        # Convert to coherence score (0-1, higher is better)
        coherence = max(0.0, 1.0 - cv)
        
        return min(1.0, coherence)
    
    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get sklearn-specific capabilities."""
        return {
            "algorithm": self._config.algorithm,
            "max_features": self._config.max_features,
            "ngram_range": self._config.ngram_range,
            "supports_lda": True,
            "supports_nmf": True,
            "supports_kmeans": True,
            "vectorization": "tfidf" if self._config.algorithm != "lda" else "count"
        }