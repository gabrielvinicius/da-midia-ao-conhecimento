# src/topic_modeling/infrastructure/providers/gensim_provider.py
"""
Gensim topic modeling provider - OCP and SRP compliance.
"""
import asyncio
from typing import Dict, Any, List
import numpy as np

try:
    import gensim
    from gensim import corpora
    from gensim.models import LdaModel, LsiModel, HdpModel
    from gensim.models.coherencemodel import CoherenceModel
    from gensim.parsing.preprocessing import preprocess_string, DEFAULT_FILTERS
    GENSIM_AVAILABLE = True
except ImportError:
    GENSIM_AVAILABLE = False




class GensimConfiguration:
    """Configuration for Gensim topic modeling - SRP compliance."""
    
    def __init__(
        self,
        algorithm: str = "lda",  # lda, lsi, hdp
        max_text_length: int = 200000,
        min_word_count: int = 5,
        no_below: int = 2,
        no_above: float = 0.8,
        keep_n: int = 2000,
        passes: int = 10,
        iterations: int = 400,
        random_state: int = 42
    ):
        self.algorithm = algorithm
        self.max_text_length = max_text_length
        self.min_word_count = min_word_count
        self.no_below = no_below
        self.no_above = no_above
        self.keep_n = keep_n
        self.passes = passes
        self.iterations = iterations
        self.random_state = random_state
    
    def get_config(self) -> Dict[str, Any]:
        """Get configuration dictionary."""
        return {
            "algorithm": self.algorithm,
            "max_text_length": self.max_text_length,
            "min_word_count": self.min_word_count,
            "no_below": self.no_below,
            "no_above": self.no_above,
            "keep_n": self.keep_n,
            "passes": self.passes,
            "iterations": self.iterations,
            "random_state": self.random_state
        }
    
    def validate_config(self) -> bool:
        """Validate configuration."""
        valid_algorithms = ["lda", "lsi", "hdp"]
        return (
            self.algorithm in valid_algorithms and
            self.max_text_length > 0 and
            self.min_word_count > 0 and
            self.no_below > 0 and
            0.0 < self.no_above <= 1.0 and
            self.passes > 0 and
            self.iterations > 0
        )
    
    def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        # Gensim can work with any language, but we list common ones
        return ["en", "es", "fr", "de", "it", "pt", "ru", "zh", "ja", "ar"]
    
    def get_max_text_length(self) -> int:
        """Get maximum text length."""
        return self.max_text_length


class GensimTopicModelingProvider:
    """
    Gensim topic modeling provider.
    Follows OCP - can be extended without modification.
    """
    
    def __init__(self, config: GensimConfiguration):
        if not GENSIM_AVAILABLE:
            raise TopicModelingProviderError("Gensim is not installed. Install with: pip install gensim")
        
        super().__init__(config)
        self._config = config
    
    @property
    def provider_name(self) -> str:
        """Provider identifier."""
        return f"gensim_{self._config.algorithm}"
    
    def _initialize_provider(self) -> None:
        """Initialize Gensim components."""
        try:
            # Set random seed for reproducibility
            np.random.seed(self._config.random_state)
        except Exception as e:
            raise TopicModelingProviderError(f"Failed to initialize Gensim provider: {e}") from e
    
    async def _do_extract_topics(
        self, 
        text: str, 
        language: str, 
        num_topics: int,
        num_words_per_topic: int
    ) -> List[Dict[str, Any]]:
        """Actual topic extraction implementation using Gensim."""
        try:
            # Preprocess and tokenize text
            documents = await self._preprocess_for_gensim(text)
            
            # Create dictionary and corpus
            dictionary = corpora.Dictionary(documents)
            
            # Filter extremes
            dictionary.filter_extremes(
                no_below=self._config.no_below,
                no_above=self._config.no_above,
                keep_n=self._config.keep_n
            )
            
            # Create corpus
            corpus = [dictionary.doc2bow(doc) for doc in documents]
            
            if not corpus or len(dictionary) == 0:
                raise TopicModelingProviderError("No valid tokens found in text")
            
            # Create and train model
            model = await self._create_and_train_model(
                corpus, dictionary, num_topics
            )
            
            # Extract topics
            topics = await self._extract_topics_from_gensim_model(
                model, dictionary, corpus, num_words_per_topic
            )
            
            return topics
            
        except Exception as e:
            raise TopicModelingProviderError(f"Gensim topic extraction failed: {e}") from e
    
    async def get_supported_languages(self) -> List[str]:
        """Get supported languages."""
        return self._config.get_supported_languages()
    
    def _supports_multilingual(self) -> bool:
        """Whether provider supports multilingual processing."""
        return True
    
    def _supports_dynamic_topics(self) -> bool:
        """Whether provider supports dynamic topic number detection."""
        return self._config.algorithm == "hdp"  # HDP can determine topic number automatically
    
    def _supports_coherence_scoring(self) -> bool:
        """Whether provider supports coherence scoring."""
        return True
    
    async def _preprocess_for_gensim(self, text: str) -> List[List[str]]:
        """Preprocess text for Gensim."""
        # Split text into documents
        documents = self._split_text_into_documents(text)
        
        # Process each document
        processed_docs = []
        for doc in documents:
            # Use Gensim's preprocessing
            tokens = await asyncio.to_thread(
                preprocess_string, 
                doc, 
                DEFAULT_FILTERS
            )
            
            # Filter short tokens
            tokens = [token for token in tokens if len(token) > 2]
            
            if tokens:  # Only add non-empty documents
                processed_docs.append(tokens)
        
        return processed_docs
    
    def _split_text_into_documents(self, text: str) -> List[str]:
        """Split text into documents."""
        # Split by paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        # If too few paragraphs, split by sentences
        if len(paragraphs) < 5:
            import re
            sentences = re.split(r'[.!?]+', text)
            sentences = [s.strip() for s in sentences if s.strip() and len(s) > 30]
            
            if len(sentences) >= 5:
                return sentences
        
        # If still too few, create artificial documents by splitting text
        if len(paragraphs) < 3:
            words = text.split()
            chunk_size = max(50, len(words) // 5)  # At least 50 words per chunk
            
            chunks = []
            for i in range(0, len(words), chunk_size):
                chunk = ' '.join(words[i:i + chunk_size])
                if chunk.strip():
                    chunks.append(chunk)
            
            return chunks if chunks else [text]
        
        return paragraphs
    
    async def _create_and_train_model(
        self, 
        corpus, 
        dictionary, 
        num_topics: int
    ):
        """Create and train Gensim model."""
        if self._config.algorithm == "lda":
            model = LdaModel(
                corpus=corpus,
                id2word=dictionary,
                num_topics=num_topics,
                passes=self._config.passes,
                iterations=self._config.iterations,
                random_state=self._config.random_state,
                alpha='auto',
                per_word_topics=True
            )
        elif self._config.algorithm == "lsi":
            model = LsiModel(
                corpus=corpus,
                id2word=dictionary,
                num_topics=num_topics
            )
        elif self._config.algorithm == "hdp":
            model = HdpModel(
                corpus=corpus,
                id2word=dictionary,
                random_state=self._config.random_state
            )
        else:
            raise TopicModelingProviderError(f"Unknown algorithm: {self._config.algorithm}")
        
        return model
    
    async def _extract_topics_from_gensim_model(
        self, 
        model, 
        dictionary, 
        corpus, 
        num_words_per_topic: int
    ) -> List[Dict[str, Any]]:
        """Extract topics from Gensim model."""
        topics = []
        
        if hasattr(model, 'show_topics'):
            # Get topics from model
            if self._config.algorithm == "hdp":
                # HDP determines number of topics automatically
                model_topics = model.show_topics(
                    num_topics=-1,  # Show all topics
                    num_words=num_words_per_topic,
                    formatted=False
                )
            else:
                model_topics = model.show_topics(
                    num_topics=model.num_topics,
                    num_words=num_words_per_topic,
                    formatted=False
                )
            
            for topic_id, topic_words in model_topics:
                # Extract words and scores
                words = [word for word, score in topic_words]
                scores = [score for word, score in topic_words]
                
                # Calculate coherence score
                coherence_score = await self._calculate_gensim_coherence(
                    model, dictionary, corpus, [words]
                )
                
                topic_dict = {
                    "words": words,
                    "scores": scores,
                    "raw_scores": scores,
                    "coherence_score": coherence_score,
                    "dominant_words": words[:3]
                }
                
                topics.append(topic_dict)
        
        return topics
    
    async def _calculate_gensim_coherence(
        self, 
        model, 
        dictionary, 
        corpus, 
        topics: List[List[str]]
    ) -> float:
        """Calculate coherence score using Gensim."""
        try:
            # Create corpus for coherence calculation
            corpus_for_coherence = [dictionary.doc2bow(doc) for doc in topics]
            
            if not corpus_for_coherence:
                return 0.0
            
            # Calculate coherence using c_v measure
            coherence_model = CoherenceModel(
                topics=topics,
                corpus=corpus,
                dictionary=dictionary,
                coherence='c_v'
            )
            
            coherence_score = await asyncio.to_thread(coherence_model.get_coherence)
            
            # Normalize to 0-1 range
            return max(0.0, min(1.0, coherence_score))
            
        except Exception:
            # Fallback to simple coherence calculation
            return 0.5
    
    async def _get_provider_specific_capabilities(self) -> Dict[str, Any]:
        """Get Gensim-specific capabilities."""
        return {
            "algorithm": self._config.algorithm,
            "passes": self._config.passes,
            "iterations": self._config.iterations,
            "supports_lda": True,
            "supports_lsi": True,
            "supports_hdp": True,
            "supports_coherence_cv": True,
            "supports_perplexity": True,
            "automatic_topic_detection": self._config.algorithm == "hdp"
        }