"""
Sentiment Analysis Template Methods using Template Method Pattern
"""
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum
import re

from src.shared.patterns.template_method import TemplateMethodBase, ProcessingResult, TemplateMethodFactory
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis


class SentimentLabel(str, Enum):
    """Sentiment labels"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"


class AnalysisGranularity(str, Enum):
    """Analysis granularity levels"""
    DOCUMENT = "document"  # Entire document
    SENTENCE = "sentence"  # Sentence-level
    ASPECT = "aspect"  # Aspect-based sentiment


@dataclass
class SentimentInput:
    """Input data for sentiment analysis template methods"""
    text: str
    language: str = "en"
    granularity: AnalysisGranularity = AnalysisGranularity.DOCUMENT
    aspects: Optional[List[str]] = None  # For aspect-based analysis
    context: Optional[str] = None  # Additional context
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.aspects is None:
            self.aspects = []


class BaseSentimentAnalysisTemplate(TemplateMethodBase[SentimentInput, SentimentAnalysis]):
    """
    Base template for all sentiment analysis algorithms.
    Defines the common structure for sentiment analysis processing.
    """
    
    def __init__(self, provider_name: str, model_name: str = None):
        super().__init__(f"{provider_name}SentimentAnalysisTemplate")
        self.provider_name = provider_name
        self.model_name = model_name or "default"
        self.processed_text = None
        self.sentiment_result = None
        self.text_segments = []
    
    async def _initialize(self, input_data: SentimentInput, options: Dict[str, Any]) -> Any:
        """Initialize sentiment analysis session"""
        self.processing_result.add_metadata("provider", self.provider_name)
        self.processing_result.add_metadata("model", self.model_name)
        self.processing_result.add_metadata("language", input_data.language)
        self.processing_result.add_metadata("granularity", input_data.granularity.value)
        
        # Initialize provider-specific resources
        await self._initialize_provider(input_data, options)
        
        return {
            "provider": self.provider_name,
            "model": self.model_name,
            "session_id": f"{self.provider_name}_{hash(input_data.text) % 10000}"
        }
    
    async def _validate(self, input_data: SentimentInput, options: Dict[str, Any]) -> bool:
        """Validate text input"""
        
        # Check text content
        if not input_data.text or len(input_data.text.strip()) == 0:
            self.processing_result.add_error("Text content is empty")
            return False
        
        # Check text length limits
        min_text_length = options.get("min_text_length", 3)
        max_text_length = options.get("max_text_length", 500000)
        
        text_length = len(input_data.text)
        if text_length < min_text_length:
            self.processing_result.add_error(
                f"Text too short: {text_length} chars (minimum: {min_text_length})"
            )
            return False
        
        if text_length > max_text_length:
            self.processing_result.add_error(
                f"Text too long: {text_length} chars (maximum: {max_text_length})"
            )
            return False
        
        # Check language support
        supported_languages = await self._get_supported_languages()
        if input_data.language not in supported_languages:
            self.processing_result.add_error(
                f"Language '{input_data.language}' not supported. "
                f"Supported: {', '.join(supported_languages)}"
            )
            return False
        
        # Validate aspects for aspect-based analysis
        if input_data.granularity == AnalysisGranularity.ASPECT:
            if not input_data.aspects:
                self.processing_result.add_error("Aspects required for aspect-based analysis")
                return False
        
        # Provider-specific validation
        return await self._validate_provider_specific(input_data, options)
    
    async def _preprocess(self, input_data: SentimentInput, options: Dict[str, Any]) -> Any:
        """Preprocess text for sentiment analysis"""
        
        # Clean and normalize text
        cleaned_text = await self._clean_text(input_data.text, options)
        
        # Segment text based on granularity
        self.text_segments = await self._segment_text(
            cleaned_text, 
            input_data.granularity, 
            options
        )
        
        # Apply preprocessing specific to analysis type
        self.processed_text = await self._preprocess_for_analysis_type(
            cleaned_text,
            input_data.granularity,
            input_data.aspects,
            options
        )
        
        # Extract linguistic features
        features = await self._extract_linguistic_features(self.processed_text, options)
        
        self.processing_result.add_metadata("preprocessing", {
            "original_length": len(input_data.text),
            "cleaned_length": len(cleaned_text),
            "processed_length": len(self.processed_text),
            "segments_created": len(self.text_segments),
            "features_extracted": bool(features)
        })
        
        return self.processed_text
    
    async def _process(self, input_data: SentimentInput, options: Dict[str, Any]) -> SentimentAnalysis:
        """Core sentiment analysis processing"""
        
        # Use processed text
        text_to_analyze = self.processed_text or input_data.text
        
        # Analyze sentiment based on granularity
        if input_data.granularity == AnalysisGranularity.DOCUMENT:
            sentiment_results = await self._analyze_document_sentiment(
                text_to_analyze, input_data, options
            )
        elif input_data.granularity == AnalysisGranularity.SENTENCE:
            sentiment_results = await self._analyze_sentence_sentiment(
                text_to_analyze, input_data, options
            )
        elif input_data.granularity == AnalysisGranularity.ASPECT:
            sentiment_results = await self._analyze_aspect_sentiment(
                text_to_analyze, input_data, options
            )
        else:
            raise ValueError(f"Unsupported granularity: {input_data.granularity}")
        
        # Create sentiment analysis object
        self.sentiment_result = SentimentAnalysis(
            text=input_data.text,
            sentiment=sentiment_results.get("overall_sentiment", SentimentLabel.NEUTRAL),
            confidence=sentiment_results.get("confidence", 0.5),
            scores=sentiment_results.get("scores", {}),
            language=input_data.language,
            provider=self.provider_name,
            model=self.model_name,
            metadata=input_data.metadata
        )
        
        # Add detailed results
        if "sentence_sentiments" in sentiment_results:
            self.sentiment_result.sentence_sentiments = sentiment_results["sentence_sentiments"]
        
        if "aspect_sentiments" in sentiment_results:
            self.sentiment_result.aspect_sentiments = sentiment_results["aspect_sentiments"]
        
        return self.sentiment_result
    
    async def _postprocess(self, input_data: SentimentInput, options: Dict[str, Any]) -> Any:
        """Post-process sentiment analysis results"""
        
        if not self.sentiment_result:
            return None
        
        # Apply confidence calibration
        calibrated_confidence = await self._calibrate_confidence(
            self.sentiment_result,
            options
        )
        
        # Extract emotion indicators
        emotions = await self._extract_emotions(
            self.sentiment_result,
            options
        )
        
        # Calculate sentiment trends
        trends = await self._calculate_sentiment_trends(
            self.sentiment_result,
            options
        )
        
        # Update sentiment result with post-processed data
        self.sentiment_result.confidence = calibrated_confidence
        if emotions:
            self.sentiment_result.emotions = emotions
        if trends:
            self.sentiment_result.trends = trends
        
        self.processing_result.add_metadata("postprocessing", {
            "confidence_calibrated": calibrated_confidence != self.sentiment_result.confidence,
            "emotions_extracted": bool(emotions),
            "trends_calculated": bool(trends)
        })
        
        return self.sentiment_result
    
    async def _finalize(self, input_data: SentimentInput, options: Dict[str, Any]) -> SentimentAnalysis:
        """Finalize sentiment analysis and cleanup"""
        
        if not self.sentiment_result:
            raise ValueError("No sentiment analysis result available")
        
        # Add final metadata
        self.sentiment_result.processing_metadata = {
            "provider": self.provider_name,
            "model": self.model_name,
            "processing_time": self.processing_result.processing_time,
            "text_length": len(input_data.text),
            "segments_analyzed": len(self.text_segments)
        }
        
        # Cleanup provider resources
        await self._cleanup_provider()
        
        # Set final result
        self.processing_result.result = self.sentiment_result
        
        return self.sentiment_result
    
    def _should_preprocess(self) -> bool:
        """Enable preprocessing by default"""
        return True
    
    def _should_postprocess(self) -> bool:
        """Enable postprocessing by default"""
        return True
    
    # Abstract methods for provider-specific implementation
    
    async def _initialize_provider(self, input_data: SentimentInput, options: Dict[str, Any]) -> None:
        """Initialize provider-specific resources. Override in subclasses."""
        pass
    
    async def _get_supported_languages(self) -> List[str]:
        """Get supported languages. Override in subclasses."""
        return ["en", "es", "fr", "de", "it", "pt", "ru", "ja", "ko", "zh"]
    
    async def _validate_provider_specific(self, input_data: SentimentInput, options: Dict[str, Any]) -> bool:
        """Provider-specific validation. Override in subclasses."""
        return True
    
    async def _analyze_document_sentiment(
        self, 
        text: str, 
        input_data: SentimentInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze document-level sentiment. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _analyze_document_sentiment")
    
    async def _cleanup_provider(self) -> None:
        """Cleanup provider resources. Override in subclasses."""
        pass
    
    # Helper methods with default implementations
    
    async def _clean_text(self, text: str, options: Dict[str, Any]) -> str:
        """Clean and normalize text for sentiment analysis"""
        
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', text)
        
        # Handle mentions and hashtags
        if options.get("preserve_social_markers", False):
            # Keep @ mentions and # hashtags as-is
            pass
        else:
            # Remove @ mentions and # hashtags
            cleaned = re.sub(r'@\w+', '', cleaned)
            cleaned = re.sub(r'#\w+', '', cleaned)
        
        # Remove URLs
        cleaned = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', cleaned)
        
        # Handle emoticons and emojis
        if not options.get("preserve_emoticons", True):
            # Remove common emoticons
            emoticon_pattern = r'[;:=8][\-o\*\']?[\)\(\[\]/\\OpP]'
            cleaned = re.sub(emoticon_pattern, '', cleaned)
        
        return cleaned.strip()
    
    async def _segment_text(
        self, 
        text: str, 
        granularity: AnalysisGranularity, 
        options: Dict[str, Any]
    ) -> List[str]:
        """Segment text based on analysis granularity"""
        
        if granularity == AnalysisGranularity.DOCUMENT:
            return [text]
        elif granularity == AnalysisGranularity.SENTENCE:
            # Split into sentences
            sentences = re.split(r'[.!?]+', text)
            return [s.strip() for s in sentences if s.strip()]
        elif granularity == AnalysisGranularity.ASPECT:
            # For aspect-based analysis, we might segment by paragraphs or sentences
            paragraphs = text.split('\n\n')
            return [p.strip() for p in paragraphs if p.strip()]
        else:
            return [text]
    
    async def _preprocess_for_analysis_type(
        self, 
        text: str, 
        granularity: AnalysisGranularity,
        aspects: List[str],
        options: Dict[str, Any]
    ) -> str:
        """Apply preprocessing specific to analysis type"""
        
        if granularity == AnalysisGranularity.ASPECT and aspects:
            # For aspect-based analysis, emphasize aspect-related terms
            for aspect in aspects:
                # Highlight aspect terms (simple approach)
                pattern = rf'\b{re.escape(aspect)}\b'
                text = re.sub(pattern, f"[ASPECT]{aspect}[/ASPECT]", text, flags=re.IGNORECASE)
        
        return text
    
    async def _extract_linguistic_features(self, text: str, options: Dict[str, Any]) -> Optional[Dict]:
        """Extract linguistic features for sentiment analysis"""
        
        if not options.get("extract_features", False):
            return None
        
        # Basic linguistic features
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        
        # Count sentiment indicators
        positive_words = sum(1 for word in words if word.lower() in 
                           ['good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic', 'love', 'like'])
        negative_words = sum(1 for word in words if word.lower() in 
                           ['bad', 'terrible', 'awful', 'horrible', 'hate', 'dislike', 'worst', 'sad'])
        
        # Count intensifiers
        intensifiers = sum(1 for word in words if word.lower() in 
                         ['very', 'extremely', 'really', 'totally', 'absolutely', 'completely'])
        
        # Count negations
        negations = sum(1 for word in words if word.lower() in 
                       ['not', 'no', 'never', 'nothing', 'nowhere', 'nobody'])
        
        return {
            "word_count": len(words),
            "sentence_count": len([s for s in sentences if s.strip()]),
            "positive_words": positive_words,
            "negative_words": negative_words,
            "intensifiers": intensifiers,
            "negations": negations,
            "avg_word_length": sum(len(word) for word in words) / len(words) if words else 0
        }
    
    async def _analyze_sentence_sentiment(
        self, 
        text: str, 
        input_data: SentimentInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze sentiment at sentence level"""
        
        sentence_sentiments = []
        overall_scores = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
        
        for segment in self.text_segments:
            # Analyze each sentence (using document method as fallback)
            segment_result = await self._analyze_document_sentiment(segment, input_data, options)
            
            sentence_sentiments.append({
                "text": segment,
                "sentiment": segment_result["overall_sentiment"],
                "confidence": segment_result["confidence"],
                "scores": segment_result["scores"]
            })
            
            # Aggregate scores
            for label, score in segment_result["scores"].items():
                if label in overall_scores:
                    overall_scores[label] += score
        
        # Normalize overall scores
        total_sentences = len(sentence_sentiments)
        if total_sentences > 0:
            for label in overall_scores:
                overall_scores[label] /= total_sentences
        
        # Determine overall sentiment
        overall_sentiment = max(overall_scores, key=overall_scores.get)
        overall_confidence = max(overall_scores.values())
        
        return {
            "overall_sentiment": SentimentLabel(overall_sentiment),
            "confidence": overall_confidence,
            "scores": overall_scores,
            "sentence_sentiments": sentence_sentiments
        }
    
    async def _analyze_aspect_sentiment(
        self, 
        text: str, 
        input_data: SentimentInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze sentiment for specific aspects"""
        
        aspect_sentiments = []
        overall_scores = {"positive": 0.0, "negative": 0.0, "neutral": 0.0}
        
        for aspect in input_data.aspects:
            # Find sentences/segments containing the aspect
            aspect_segments = []
            for segment in self.text_segments:
                if aspect.lower() in segment.lower():
                    aspect_segments.append(segment)
            
            if aspect_segments:
                # Analyze sentiment for this aspect
                aspect_text = '. '.join(aspect_segments)
                aspect_result = await self._analyze_document_sentiment(aspect_text, input_data, options)
                
                aspect_sentiments.append({
                    "aspect": aspect,
                    "sentiment": aspect_result["overall_sentiment"],
                    "confidence": aspect_result["confidence"],
                    "scores": aspect_result["scores"],
                    "relevant_text": aspect_text[:200] + "..." if len(aspect_text) > 200 else aspect_text
                })
                
                # Aggregate scores
                for label, score in aspect_result["scores"].items():
                    if label in overall_scores:
                        overall_scores[label] += score
        
        # Normalize overall scores
        if aspect_sentiments:
            for label in overall_scores:
                overall_scores[label] /= len(aspect_sentiments)
        
        # Determine overall sentiment
        overall_sentiment = max(overall_scores, key=overall_scores.get) if overall_scores else "neutral"
        overall_confidence = max(overall_scores.values()) if overall_scores else 0.5
        
        return {
            "overall_sentiment": SentimentLabel(overall_sentiment),
            "confidence": overall_confidence,
            "scores": overall_scores,
            "aspect_sentiments": aspect_sentiments
        }
    
    async def _calibrate_confidence(self, sentiment_result: SentimentAnalysis, options: Dict[str, Any]) -> float:
        """Calibrate confidence score based on various factors"""
        
        original_confidence = sentiment_result.confidence
        
        # Adjust confidence based on text length
        text_length = len(sentiment_result.text)
        if text_length < 20:  # Very short text
            return original_confidence * 0.8
        elif text_length > 1000:  # Long text, usually more reliable
            return min(1.0, original_confidence * 1.1)
        
        return original_confidence
    
    async def _extract_emotions(self, sentiment_result: SentimentAnalysis, options: Dict[str, Any]) -> Optional[Dict]:
        """Extract emotional indicators from text"""
        
        if not options.get("extract_emotions", False):
            return None
        
        emotion_keywords = {
            "joy": ["happy", "joy", "excited", "thrilled", "delighted"],
            "anger": ["angry", "mad", "furious", "irritated", "annoyed"],
            "sadness": ["sad", "depressed", "disappointed", "grief", "sorrow"],
            "fear": ["afraid", "scared", "worried", "anxious", "nervous"],
            "surprise": ["surprised", "amazed", "shocked", "astonished"]
        }
        
        text_lower = sentiment_result.text.lower()
        emotions = {}
        
        for emotion, keywords in emotion_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            if count > 0:
                emotions[emotion] = count / len(keywords)  # Normalize
        
        return emotions if emotions else None
    
    async def _calculate_sentiment_trends(self, sentiment_result: SentimentAnalysis, options: Dict[str, Any]) -> Optional[Dict]:
        """Calculate sentiment trends if sentence-level analysis is available"""
        
        if not hasattr(sentiment_result, 'sentence_sentiments') or not sentiment_result.sentence_sentiments:
            return None
        
        sentiments = [s["sentiment"] for s in sentiment_result.sentence_sentiments]
        
        # Calculate trend (getting more positive, negative, or stable)
        positive_count = sentiments.count(SentimentLabel.POSITIVE)
        negative_count = sentiments.count(SentimentLabel.NEGATIVE)
        neutral_count = sentiments.count(SentimentLabel.NEUTRAL)
        
        # Simple trend analysis: compare first half with second half
        mid_point = len(sentiments) // 2
        first_half = sentiments[:mid_point]
        second_half = sentiments[mid_point:]
        
        first_positive = first_half.count(SentimentLabel.POSITIVE) / len(first_half) if first_half else 0
        second_positive = second_half.count(SentimentLabel.POSITIVE) / len(second_half) if second_half else 0
        
        trend = "stable"
        if second_positive > first_positive + 0.2:
            trend = "improving"
        elif second_positive < first_positive - 0.2:
            trend = "declining"
        
        return {
            "overall_trend": trend,
            "positive_ratio": positive_count / len(sentiments),
            "negative_ratio": negative_count / len(sentiments),
            "neutral_ratio": neutral_count / len(sentiments)
        }


class HuggingFaceSentimentTemplate(BaseSentimentAnalysisTemplate):
    """HuggingFace-specific sentiment analysis template"""
    
    def __init__(self, model_name: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"):
        super().__init__("huggingface", model_name)
        self.hf_model = None
        self.hf_tokenizer = None
    
    async def _initialize_provider(self, input_data: SentimentInput, options: Dict[str, Any]) -> None:
        """Initialize HuggingFace model"""
        try:
            # In practice, load actual HuggingFace model
            self.hf_model = f"hf_sentiment_model_{self.model_name}"
            self.hf_tokenizer = f"hf_sentiment_tokenizer_{self.model_name}"
            self.processing_result.add_metadata("hf_model_loaded", True)
        except Exception as e:
            self.processing_result.add_error(f"Failed to load HuggingFace model: {e}")
    
    async def _analyze_document_sentiment(
        self, 
        text: str, 
        input_data: SentimentInput, 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze sentiment using HuggingFace model"""
        
        if not self.hf_model:
            raise ValueError("HuggingFace model not initialized")
        
        # HuggingFace-specific processing
        # In practice, use actual model inference
        
        # Mock sentiment analysis result
        text_lower = text.lower()
        
        # Simple rule-based mock (replace with actual model inference)
        positive_score = 0.1 + min(0.8, text_lower.count('good') * 0.2 + text_lower.count('great') * 0.3)
        negative_score = 0.1 + min(0.8, text_lower.count('bad') * 0.2 + text_lower.count('terrible') * 0.3)
        neutral_score = 1.0 - positive_score - negative_score
        
        # Normalize scores
        total = positive_score + negative_score + neutral_score
        scores = {
            "positive": positive_score / total,
            "negative": negative_score / total,
            "neutral": neutral_score / total
        }
        
        overall_sentiment = max(scores, key=scores.get)
        confidence = max(scores.values())
        
        self.processing_result.add_metadata("hf_processing", {
            "model_name": self.model_name,
            "text_length": len(text),
            "tokenized_length": len(text.split())  # Mock tokenization
        })
        
        return {
            "overall_sentiment": SentimentLabel(overall_sentiment),
            "confidence": confidence,
            "scores": scores
        }


# Register templates in factory
def register_sentiment_analysis_templates():
    """Register all sentiment analysis templates"""
    
    # HuggingFace templates
    TemplateMethodFactory.register_template(
        "hf_roberta_sentiment", 
        lambda: HuggingFaceSentimentTemplate("cardiffnlp/twitter-roberta-base-sentiment-latest")
    )
    TemplateMethodFactory.register_template(
        "hf_bert_sentiment", 
        lambda: HuggingFaceSentimentTemplate("nlptown/bert-base-multilingual-uncased-sentiment")
    )
    TemplateMethodFactory.register_template(
        "hf_distilbert_sentiment", 
        lambda: HuggingFaceSentimentTemplate("distilbert-base-uncased-finetuned-sst-2-english")
    )