"""
Sentiment Analyzer Service - Single Responsibility: High-level sentiment analysis orchestration
Follows SRP by handling only sentiment analysis workflow coordination.
"""
from typing import Dict, List, Any, Optional
from uuid import UUID
import structlog
import time

from src.sentiment_analysis.domain.interfaces import (
    ISentimentAnalyzer, ISentimentAnalysisService, ISentimentRepository, 
    ISentimentCache, ISentimentValidator, ISentimentMetrics,
    SentimentProvider, SentimentLabel
)
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult
from src.media_management.domain.interfaces import IMediaRepository

logger = structlog.get_logger(__name__)


class SentimentAnalyzer(ISentimentAnalyzer):
    """
    High-level sentiment analyzer service following SOLID principles.
    
    Single Responsibility: Orchestrate sentiment analysis workflow.
    Open/Closed: Extensible through provider interfaces.
    Dependency Inversion: Depends on abstractions, not concretions.
    """
    
    def __init__(
        self,
        sentiment_services: Dict[str, ISentimentAnalysisService],
        sentiment_repository: ISentimentRepository,
        media_repository: IMediaRepository,
        cache_service: Optional[ISentimentCache] = None,
        validator_service: Optional[ISentimentValidator] = None,
        metrics_service: Optional[ISentimentMetrics] = None
    ):
        self.sentiment_services = sentiment_services
        self.sentiment_repository = sentiment_repository
        self.media_repository = media_repository
        self.cache_service = cache_service
        self.validator_service = validator_service
        self.metrics_service = metrics_service
    
    async def analyze_media(
        self,
        media_id: UUID,
        provider: SentimentProvider = SentimentProvider.HUGGINGFACE,
        options: Optional[Dict[str, Any]] = None
    ) -> UUID:
        """
        Analyze sentiment for media content.
        
        Args:
            media_id: ID of media to analyze
            provider: Sentiment analysis provider to use
            options: Additional analysis options
            
        Returns:
            Analysis result ID
        """
        start_time = time.time()
        
        try:
            # Get media content
            media = await self.media_repository.find_by_id(media_id)
            if not media:
                raise ValueError(f"Media with ID {media_id} not found")
            
            # Check if analysis already exists
            existing_result = await self.sentiment_repository.find_by_media_id(media_id)
            if existing_result and not options.get("force_reanalysis", False):
                logger.info(
                    "sentiment_analysis.existing_result_found",
                    media_id=str(media_id),
                    result_id=str(existing_result.id)
                )
                return existing_result.id
            
            # Get text content from media (assuming transcription exists)
            text_content = self._extract_text_from_media(media)
            if not text_content:
                raise ValueError("No text content available for sentiment analysis")
            
            # Check cache if available
            if self.cache_service:
                cached_result = await self._get_cached_result(text_content, provider)
                if cached_result:
                    logger.info("sentiment_analysis.cache_hit", media_id=str(media_id))
                    return await self._save_result_from_cache(media_id, cached_result, provider)
            
            # Perform sentiment analysis
            sentiment_service = self._get_sentiment_service(provider)
            language = options.get("language") if options else None
            
            analysis_result = await sentiment_service.analyze(text_content, language)
            
            # Validate result if validator available
            if self.validator_service:
                is_valid = self.validator_service.validate_analysis_result(analysis_result)
                if not is_valid:
                    logger.warning(
                        "sentiment_analysis.invalid_result",
                        media_id=str(media_id),
                        provider=provider.value
                    )
                    analysis_result["is_reliable"] = False
            
            # Create and save result
            result = await self._create_and_save_result(
                media_id, analysis_result, provider, options
            )
            
            # Cache result if service available
            if self.cache_service:
                await self._cache_result(text_content, provider, analysis_result)
            
            # Track metrics
            if self.metrics_service:
                processing_time = (time.time() - start_time) * 1000
                await self.metrics_service.track_analysis_request(
                    provider=provider,
                    success=True,
                    duration=processing_time,
                    text_length=len(text_content)
                )
            
            logger.info(
                "sentiment_analysis.completed",
                media_id=str(media_id),
                result_id=str(result.id),
                provider=provider.value,
                sentiment=analysis_result.get("label"),
                score=analysis_result.get("score")
            )
            
            return result.id
            
        except Exception as e:
            # Track error metrics
            if self.metrics_service:
                processing_time = (time.time() - start_time) * 1000
                await self.metrics_service.track_analysis_request(
                    provider=provider,
                    success=False,
                    duration=processing_time,
                    text_length=0
                )
            
            logger.error(
                "sentiment_analysis.failed",
                media_id=str(media_id),
                provider=provider.value,
                error=str(e)
            )
            raise
    
    async def reanalyze_media(
        self,
        media_id: UUID,
        provider: Optional[SentimentProvider] = None
    ) -> UUID:
        """
        Re-analyze media with different provider or updated settings.
        
        Args:
            media_id: ID of media to re-analyze
            provider: Optional different provider to use
            
        Returns:
            New analysis result ID
        """
        # Get existing result to determine provider if not specified
        if not provider:
            existing_result = await self.sentiment_repository.find_by_media_id(media_id)
            if existing_result:
                provider = existing_result.get_provider()
            else:
                provider = SentimentProvider.HUGGINGFACE
        
        options = {"force_reanalysis": True}
        return await self.analyze_media(media_id, provider, options)
    
    async def analyze_text_directly(
        self,
        text: str,
        provider: SentimentProvider = SentimentProvider.HUGGINGFACE,
        user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of text directly without storing.
        
        Args:
            text: Text to analyze
            provider: Sentiment analysis provider
            user_id: Optional user ID for tracking
            
        Returns:
            Sentiment analysis result
        """
        start_time = time.time()
        
        try:
            # Validate text input if validator available
            if self.validator_service:
                validation_result = self.validator_service.validate_text_input(text)
                if not validation_result.get("is_valid", True):
                    raise ValueError(validation_result.get("error", "Invalid text input"))
            
            # Check cache
            if self.cache_service:
                cached_result = await self._get_cached_result(text, provider)
                if cached_result:
                    logger.info("sentiment_analysis.direct_cache_hit", provider=provider.value)
                    return cached_result
            
            # Perform analysis
            sentiment_service = self._get_sentiment_service(provider)
            result = await sentiment_service.analyze(text)
            
            # Cache result
            if self.cache_service:
                await self._cache_result(text, provider, result)
            
            # Track metrics
            if self.metrics_service:
                processing_time = (time.time() - start_time) * 1000
                await self.metrics_service.track_analysis_request(
                    provider=provider,
                    success=True,
                    duration=processing_time,
                    text_length=len(text)
                )
            
            logger.info(
                "sentiment_analysis.direct_completed",
                provider=provider.value,
                sentiment=result.get("label"),
                score=result.get("score"),
                user_id=str(user_id) if user_id else None
            )
            
            return result
            
        except Exception as e:
            if self.metrics_service:
                processing_time = (time.time() - start_time) * 1000
                await self.metrics_service.track_analysis_request(
                    provider=provider,
                    success=False,
                    duration=processing_time,
                    text_length=len(text)
                )
            
            logger.error(
                "sentiment_analysis.direct_failed",
                provider=provider.value,
                error=str(e),
                user_id=str(user_id) if user_id else None
            )
            raise
    
    async def get_provider_comparison(
        self,
        text: str,
        providers: List[SentimentProvider]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Compare results across multiple providers.
        
        Args:
            text: Text to analyze
            providers: List of providers to compare
            
        Returns:
            Dictionary mapping provider names to results
        """
        comparison_results = {}
        
        for provider in providers:
            try:
                result = await self.analyze_text_directly(text, provider)
                comparison_results[provider.value] = result
            except Exception as e:
                logger.warning(
                    "sentiment_analysis.provider_comparison_failed",
                    provider=provider.value,
                    error=str(e)
                )
                comparison_results[provider.value] = {
                    "error": str(e),
                    "label": "ERROR",
                    "score": 0.0
                }
        
        # Add comparison summary
        if len(comparison_results) > 1:
            comparison_results["_summary"] = self._generate_comparison_summary(comparison_results)
        
        logger.info(
            "sentiment_analysis.provider_comparison_completed",
            providers=[p.value for p in providers],
            successful_providers=len([r for r in comparison_results.values() if r.get("label") != "ERROR"])
        )
        
        return comparison_results
    
    def _get_sentiment_service(self, provider: SentimentProvider) -> ISentimentAnalysisService:
        """Get sentiment analysis service for provider."""
        service = self.sentiment_services.get(provider.value)
        if not service:
            available_providers = list(self.sentiment_services.keys())
            raise ValueError(
                f"Provider '{provider.value}' not available. "
                f"Available providers: {available_providers}"
            )
        return service
    
    def _extract_text_from_media(self, media) -> Optional[str]:
        """Extract text content from media for analysis."""
        # This would typically get transcription text
        # For now, return a placeholder implementation
        if hasattr(media, 'transcription_text'):
            return media.transcription_text
        elif hasattr(media, 'content'):
            return media.content
        else:
            # Would integrate with transcription service to get text
            return None
    
    async def _get_cached_result(self, text: str, provider: SentimentProvider) -> Optional[Dict[str, Any]]:
        """Get cached result if available."""
        if not self.cache_service:
            return None
        
        import hashlib
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return await self.cache_service.get_cached_result(text_hash, provider)
    
    async def _cache_result(self, text: str, provider: SentimentProvider, result: Dict[str, Any]) -> None:
        """Cache analysis result."""
        if not self.cache_service:
            return
        
        import hashlib
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        await self.cache_service.cache_result(text_hash, provider, result)
    
    async def _save_result_from_cache(
        self, 
        media_id: UUID, 
        cached_result: Dict[str, Any], 
        provider: SentimentProvider
    ) -> UUID:
        """Save cached result to database."""
        return await self._create_and_save_result(media_id, cached_result, provider, None)
    
    async def _create_and_save_result(
        self,
        media_id: UUID,
        analysis_result: Dict[str, Any],
        provider: SentimentProvider,
        options: Optional[Dict[str, Any]]
    ) -> SentimentAnalysisResult:
        """Create and save sentiment analysis result."""
        result = SentimentAnalysisResult(
            media_id=media_id,
            label=analysis_result.get("label", "neutral"),
            score=analysis_result.get("score", 0.0),
            confidence=analysis_result.get("confidence", 0.0),
            provider=provider.value,
            model_name=analysis_result.get("model_name"),
            processing_time_ms=analysis_result.get("processing_time_ms"),
            text_length=analysis_result.get("text_length"),
            language=analysis_result.get("language", "en"),
            granularity=analysis_result.get("granularity", "document"),
            full_result=analysis_result,
            detailed_scores=analysis_result.get("detailed_scores"),
            emotions=analysis_result.get("emotions"),
            keywords=analysis_result.get("keywords"),
            is_reliable=analysis_result.get("is_reliable", True),
            error_message=analysis_result.get("detail") if analysis_result.get("label") == "ERROR" else None
        )
        
        return await self.sentiment_repository.save(result)
    
    def _generate_comparison_summary(self, comparison_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of provider comparison."""
        successful_results = {
            k: v for k, v in comparison_results.items() 
            if k != "_summary" and v.get("label") != "ERROR"
        }
        
        if not successful_results:
            return {"error": "No successful analyses to compare"}
        
        # Count sentiment labels
        label_counts = {}
        scores = []
        
        for result in successful_results.values():
            label = result.get("label", "neutral")
            label_counts[label] = label_counts.get(label, 0) + 1
            scores.append(result.get("score", 0.0))
        
        # Determine consensus
        most_common_label = max(label_counts, key=label_counts.get)
        agreement_percentage = (label_counts[most_common_label] / len(successful_results)) * 100
        
        return {
            "consensus_label": most_common_label,
            "agreement_percentage": agreement_percentage,
            "average_score": sum(scores) / len(scores) if scores else 0.0,
            "label_distribution": label_counts,
            "total_providers": len(successful_results),
            "is_consensus": agreement_percentage >= 50.0
        }