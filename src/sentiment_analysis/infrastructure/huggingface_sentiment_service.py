# src/sentiment_analysis/infrastructure/huggingface_sentiment_service.py
from transformers import pipeline, Pipeline
from typing import Dict, Any, List, Optional
import time
import hashlib
import structlog
from enum import Enum

logger = structlog.get_logger(__name__)


class SentimentProvider(str, Enum):
    HUGGINGFACE = "huggingface"
    OPENAI = "openai"
    CUSTOM = "custom"


class AnalysisGranularity(str, Enum):
    DOCUMENT = "document"
    SENTENCE = "sentence"
    PARAGRAPH = "paragraph"


class HuggingFaceSentimentAnalyzer:
    """
    HuggingFace sentiment analysis service following SOLID principles.
    
    Single Responsibility: Handle HuggingFace-specific sentiment analysis.
    Open/Closed: Extensible for different HuggingFace models.
    Dependency Inversion: Implements ISentimentAnalysisService interface.
    """

    def __init__(
        self, 
        model_name: str = "distilbert-base-uncased-finetuned-sst-2-english",
        emotion_model: Optional[str] = None
    ):
        try:
            logger.info("sentiment_analysis.service.init", model=model_name, provider="huggingface")
            
            # Primary sentiment analysis pipeline
            self.pipeline = pipeline("sentiment-analysis", model=model_name)
            self.model_name = model_name
            
            # Optional emotion detection pipeline
            self.emotion_pipeline = None
            if emotion_model:
                try:
                    self.emotion_pipeline = pipeline("text-classification", model=emotion_model)
                    logger.info("emotion_detection.loaded", model=emotion_model)
                except Exception as e:
                    logger.warning("emotion_detection.load_failed", error=str(e))
            
            # Supported languages (model-dependent)
            self.supported_languages = ["en"]  # Base model is English-only
            self.confidence_threshold = 0.7
            
            logger.info("sentiment_analysis.service.loaded", model=model_name)
            
        except Exception as e:
            logger.error("sentiment_analysis.service.init_failed", error=str(e))
            raise

    def get_provider_name(self) -> str:
        """Get the name of the sentiment analysis provider."""
        return "huggingface"

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return self.supported_languages.copy()

    async def analyze(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze sentiment of text.
        
        Args:
            text: Text to analyze
            language: Optional language code (currently only 'en' supported)
            
        Returns:
            Dictionary with sentiment analysis results
        """
        start_time = time.time()
        
        if not text or not text.strip():
            return {
                "label": "NEUTRAL", 
                "score": 1.0, 
                "confidence": 1.0,
                "detail": "Input text was empty.",
                "provider": self.get_provider_name(),
                "processing_time_ms": 0,
                "text_length": 0
            }

        # Validate language
        if language and language not in self.supported_languages:
            logger.warning(
                "sentiment_analysis.unsupported_language",
                language=language,
                supported=self.supported_languages
            )
            return {
                "label": "ERROR",
                "score": 0.0,
                "detail": f"Language '{language}' not supported",
                "provider": self.get_provider_name()
            }

        try:
            # Truncate text if too long
            max_length = 512  # BERT model limit
            truncated_text = text[:max_length] if len(text) > max_length else text
            
            # Perform sentiment analysis
            result = self.pipeline(truncated_text, truncation=True, max_length=max_length)
            primary_result = result[0] if isinstance(result, list) else result
            
            # Normalize label to lowercase
            label = primary_result["label"].lower()
            score = primary_result["score"]
            
            # Calculate processing time
            processing_time = (time.time() - start_time) * 1000
            
            # Build comprehensive result
            analysis_result = {
                "label": label,
                "score": score,
                "confidence": score,  # For HuggingFace, confidence = score
                "provider": self.get_provider_name(),
                "model_name": self.model_name,
                "processing_time_ms": processing_time,
                "text_length": len(text),
                "language": language or "en",
                "granularity": "document",
                "was_truncated": len(text) > max_length
            }
            
            # Add emotion analysis if available
            if self.emotion_pipeline:
                try:
                    emotion_result = self.emotion_pipeline(truncated_text)
                    emotions = {}
                    
                    if isinstance(emotion_result, list):
                        for emotion in emotion_result:
                            emotions[emotion["label"].lower()] = emotion["score"]
                    
                    analysis_result["emotions"] = emotions
                    
                except Exception as e:
                    logger.warning("emotion_analysis.failed", error=str(e))
            
            # Extract keywords (simple implementation)
            keywords = self._extract_sentiment_keywords(text, label)
            if keywords:
                analysis_result["keywords"] = keywords
            
            logger.info(
                "sentiment_analysis.completed",
                label=label,
                score=score,
                processing_time_ms=processing_time,
                text_length=len(text)
            )
            
            return analysis_result
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error("sentiment_analysis.failed", error=str(e), processing_time_ms=processing_time)
            
            return {
                "label": "ERROR",
                "score": 0.0,
                "confidence": 0.0,
                "detail": str(e),
                "provider": self.get_provider_name(),
                "processing_time_ms": processing_time,
                "text_length": len(text)
            }

    async def analyze_batch(self, texts: List[str], language: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Analyze sentiment of multiple texts in batch.
        
        Args:
            texts: List of texts to analyze
            language: Optional language code
            
        Returns:
            List of sentiment analysis results
        """
        results = []
        
        for text in texts:
            result = await self.analyze(text, language)
            results.append(result)
        
        logger.info(
            "sentiment_analysis.batch_completed",
            batch_size=len(texts),
            provider=self.get_provider_name()
        )
        
        return results

    async def analyze_with_granularity(
        self,
        text: str,
        granularity: AnalysisGranularity,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment with specific granularity.
        
        Args:
            text: Text to analyze
            granularity: Level of granularity for analysis
            language: Optional language code
            
        Returns:
            Granular sentiment analysis results
        """
        if granularity == AnalysisGranularity.DOCUMENT:
            return await self.analyze(text, language)
        
        elif granularity == AnalysisGranularity.SENTENCE:
            return await self._analyze_by_sentences(text, language)
        
        elif granularity == AnalysisGranularity.PARAGRAPH:
            return await self._analyze_by_paragraphs(text, language)
        
        else:
            # Fallback to document level
            result = await self.analyze(text, language)
            result["granularity"] = granularity.value
            return result

    async def get_confidence_threshold(self) -> float:
        """Get confidence threshold for reliable results."""
        return self.confidence_threshold

    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the service."""
        try:
            # Test with simple text
            test_result = await self.analyze("This is a test.")
            
            is_healthy = (
                test_result.get("label") != "ERROR" and
                test_result.get("score", 0) > 0
            )
            
            return {
                "status": "healthy" if is_healthy else "unhealthy",
                "provider": self.get_provider_name(),
                "model_name": self.model_name,
                "supported_languages": self.supported_languages,
                "emotion_detection_available": self.emotion_pipeline is not None,
                "test_result": test_result if is_healthy else None,
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.get_provider_name(),
                "error": str(e),
                "timestamp": time.time()
            }

    async def _analyze_by_sentences(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Analyze sentiment at sentence level."""
        import re
        
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        sentence_results = []
        for sentence in sentences:
            result = await self.analyze(sentence, language)
            sentence_results.append({
                "text": sentence,
                "sentiment": result
            })
        
        # Aggregate to document level
        positive_count = sum(1 for r in sentence_results if r["sentiment"]["label"] == "positive")
        negative_count = sum(1 for r in sentence_results if r["sentiment"]["label"] == "negative")
        neutral_count = len(sentence_results) - positive_count - negative_count
        
        # Determine overall sentiment
        if positive_count > negative_count:
            overall_label = "positive"
        elif negative_count > positive_count:
            overall_label = "negative"
        else:
            overall_label = "neutral"
        
        # Calculate average score
        avg_score = sum(r["sentiment"]["score"] for r in sentence_results) / len(sentence_results)
        
        return {
            "label": overall_label,
            "score": avg_score,
            "confidence": avg_score,
            "granularity": "sentence",
            "provider": self.get_provider_name(),
            "sentence_count": len(sentences),
            "sentence_results": sentence_results,
            "distribution": {
                "positive": positive_count,
                "negative": negative_count,
                "neutral": neutral_count
            }
        }

    async def _analyze_by_paragraphs(self, text: str, language: Optional[str] = None) -> Dict[str, Any]:
        """Analyze sentiment at paragraph level."""
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        
        paragraph_results = []
        for paragraph in paragraphs:
            result = await self.analyze(paragraph, language)
            paragraph_results.append({
                "text": paragraph[:100] + "..." if len(paragraph) > 100 else paragraph,
                "sentiment": result
            })
        
        # Aggregate results similar to sentence analysis
        positive_count = sum(1 for r in paragraph_results if r["sentiment"]["label"] == "positive")
        negative_count = sum(1 for r in paragraph_results if r["sentiment"]["label"] == "negative")
        
        if positive_count > negative_count:
            overall_label = "positive"
        elif negative_count > positive_count:
            overall_label = "negative"
        else:
            overall_label = "neutral"
        
        avg_score = sum(r["sentiment"]["score"] for r in paragraph_results) / len(paragraph_results)
        
        return {
            "label": overall_label,
            "score": avg_score,
            "confidence": avg_score,
            "granularity": "paragraph",
            "provider": self.get_provider_name(),
            "paragraph_count": len(paragraphs),
            "paragraph_results": paragraph_results
        }

    def _extract_sentiment_keywords(self, text: str, sentiment_label: str) -> List[str]:
        """Extract simple sentiment-bearing keywords."""
        import re
        
        # Simple keyword extraction based on sentiment
        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "perfect"]
        negative_words = ["bad", "terrible", "awful", "horrible", "hate", "worst", "disappointing", "poor"]
        
        words = re.findall(r'\b\w+\b', text.lower())
        
        if sentiment_label == "positive":
            keywords = [word for word in words if word in positive_words]
        elif sentiment_label == "negative":
            keywords = [word for word in words if word in negative_words]
        else:
            keywords = []
        
        return list(set(keywords))  # Remove duplicates
