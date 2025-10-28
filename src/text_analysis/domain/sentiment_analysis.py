# src/sentiment_analysis/domain/sentiment_analysis.py
import uuid
from datetime import datetime
from typing import Dict, Any, List

from sqlalchemy import Column, String, DateTime, ForeignKey, Float, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from src.sentiment_analysis.domain.analysis import SentimentLabel, SentimentProvider, AnalysisGranularity

from src.shared.infrastructure.database import Base  # Manter esta importação


class SentimentAnalysisResult(Base):
    """
    Sentiment analysis result entity following domain-driven design principles.
    
    Represents the result of sentiment analysis for a piece of content.
    """
    __tablename__ = "sentiment_analysis_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    media_id = Column(UUID(as_uuid=True), ForeignKey("media.id"), nullable=False, unique=True)
    
    # Core sentiment data
    label = Column(String, nullable=False)  # positive, negative, neutral, mixed
    score = Column(Float, nullable=False)   # confidence score 0.0-1.0
    confidence = Column(Float, nullable=True)  # normalized confidence across providers
    
    # Provider and processing info
    provider = Column(String, nullable=False, default="huggingface")
    model_name = Column(String, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    
    # Analysis metadata
    text_length = Column(Integer, nullable=True)
    language = Column(String(10), nullable=True, default="en")
    granularity = Column(String, nullable=False, default="document")
    
    # Detailed results
    full_result = Column(JSONB, nullable=True)  # Complete provider response
    detailed_scores = Column(JSONB, nullable=True)  # Granular sentiment scores
    emotions = Column(JSONB, nullable=True)  # Emotion detection if available
    keywords = Column(JSONB, nullable=True)  # Key sentiment-bearing words
    
    # Quality indicators
    is_reliable = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.detailed_scores:
            self.detailed_scores = {}
        if not self.emotions:
            self.emotions = {}
        if not self.keywords:
            self.keywords = []
    
    def get_sentiment_label(self) -> SentimentLabel:
        """Get sentiment label as enum."""
        try:
            return SentimentLabel(self.label.lower())
        except ValueError:
            return SentimentLabel.NEUTRAL
    
    def get_provider(self) -> SentimentProvider:
        """Get provider as enum."""
        try:
            return SentimentProvider(self.provider.lower())
        except ValueError:
            return SentimentProvider.HUGGINGFACE
    
    def is_positive(self) -> bool:
        """Check if sentiment is positive."""
        return self.get_sentiment_label() == SentimentLabel.POSITIVE
    
    def is_negative(self) -> bool:
        """Check if sentiment is negative."""
        return self.get_sentiment_label() == SentimentLabel.NEGATIVE
    
    def is_neutral(self) -> bool:
        """Check if sentiment is neutral."""
        return self.get_sentiment_label() == SentimentLabel.NEUTRAL
    
    def is_confident(self, threshold: float = 0.7) -> bool:
        """Check if result is confident based on threshold."""
        return self.score >= threshold
    
    def get_emotion_scores(self) -> Dict[str, float]:
        """Get emotion scores if available."""
        return self.emotions or {}
    
    def get_top_keywords(self, limit: int = 5) -> List[str]:
        """Get top sentiment-bearing keywords."""
        if not self.keywords:
            return []
        
        if isinstance(self.keywords, list):
            return self.keywords[:limit]
        elif isinstance(self.keywords, dict):
            # If keywords have scores, sort by score
            sorted_keywords = sorted(
                self.keywords.items(),
                key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0,
                reverse=True
            )
            return [keyword for keyword, _ in sorted_keywords[:limit]]
        
        return []
    
    def calculate_polarity_strength(self) -> float:
        """Calculate strength of sentiment polarity."""
        if not self.label:
            return 0.0 # Adicionar tratamento para label nulo
        if self.is_neutral():
            return 0.0
        
        # For positive/negative, strength is distance from neutral (0.5)
        return abs(self.score - 0.5) * 2
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "media_id": str(self.media_id),
            "label": self.label,
            "score": self.score,
            "confidence": self.confidence,
            "provider": self.provider,
            "model_name": self.model_name,
            "processing_time_ms": self.processing_time_ms,
            "text_length": self.text_length,
            "language": self.language,
            "granularity": self.granularity,
            "detailed_scores": self.detailed_scores,
            "emotions": self.emotions,
            "keywords": self.keywords,
            "is_reliable": self.is_reliable,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "polarity_strength": self.calculate_polarity_strength(),
            "is_confident": self.is_confident(),
            "top_keywords": self.get_top_keywords()
        }
    
    def update_from_analysis(self, analysis_data: Dict[str, Any]) -> None:
        """Update result from analysis data."""
        # Core sentiment
        self.label = analysis_data.get("label", self.label)
        self.score = analysis_data.get("score", self.score)
        
        # Additional details if available
        if "confidence" in analysis_data:
            self.confidence = analysis_data["confidence"]
        
        if "emotions" in analysis_data:
            self.emotions = analysis_data["emotions"]
        
        if "keywords" in analysis_data:
            self.keywords = analysis_data["keywords"]
        
        if "detailed_scores" in analysis_data:
            self.detailed_scores = analysis_data["detailed_scores"]
        
        # Full result for debugging/analysis
        self.full_result = analysis_data
        self.updated_at = datetime.utcnow()
    
    def mark_as_unreliable(self, reason: str) -> None:
        """Mark result as unreliable with reason."""
        self.is_reliable = False
        self.error_message = reason
        self.updated_at = datetime.utcnow()
    
    def get_sentiment_summary(self) -> str:
        """Get human-readable sentiment summary."""
        label = self.get_sentiment_label()
        strength = self.calculate_polarity_strength()
        
        if label == SentimentLabel.POSITIVE:
            if strength > 0.8:
                return "Very Positive"
            elif strength > 0.5:
                return "Positive"
            else:
                return "Slightly Positive"
        elif label == SentimentLabel.NEGATIVE:
            if strength > 0.8:
                return "Very Negative"
            elif strength > 0.5:
                return "Negative"
            else:
                return "Slightly Negative"
        elif label == SentimentLabel.MIXED:
            return "Mixed Sentiment"
        else:
            return "Neutral"


class SentimentAnalysisConfiguration(Base):
    """Configuration for sentiment analysis operations."""
    __tablename__ = "sentiment_analysis_configurations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)  # None for system config
    
    # Provider preferences
    default_provider = Column(String, nullable=False, default="huggingface")
    fallback_providers = Column(JSONB, nullable=True)  # List of fallback providers
    
    # Analysis settings
    confidence_threshold = Column(Float, default=0.7)
    enable_emotion_detection = Column(Boolean, default=False)
    enable_keyword_extraction = Column(Boolean, default=True)
    max_text_length = Column(Integer, default=5000)
    
    # Language settings
    auto_detect_language = Column(Boolean, default=True)
    supported_languages = Column(JSONB, nullable=True)
    
    # Processing preferences
    enable_caching = Column(Boolean, default=True)
    cache_ttl_hours = Column(Integer, default=24)
    enable_batch_processing = Column(Boolean, default=True)
    
    # Quality settings
    min_reliability_score = Column(Float, default=0.5)
    enable_result_validation = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Remover a lógica de valores padrão do __init__
        # if not self.fallback_providers:
        #     self.fallback_providers = ["textblob", "vader"]
        # if not self.supported_languages:
        #     self.supported_languages = ["en", "es", "fr", "de", "pt"]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "default_provider": self.default_provider,
            "fallback_providers": self.fallback_providers,
            "confidence_threshold": self.confidence_threshold,
            "enable_emotion_detection": self.enable_emotion_detection,
            "enable_keyword_extraction": self.enable_keyword_extraction,
            "max_text_length": self.max_text_length,
            "auto_detect_language": self.auto_detect_language,
            "supported_languages": self.supported_languages,
            "enable_caching": self.enable_caching,
            "cache_ttl_hours": self.cache_ttl_hours,
            "enable_batch_processing": self.enable_batch_processing,
            "min_reliability_score": self.min_reliability_score,
            "enable_result_validation": self.enable_result_validation
        }