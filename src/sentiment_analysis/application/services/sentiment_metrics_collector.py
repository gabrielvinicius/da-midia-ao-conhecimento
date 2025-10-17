# src/sentiment_analysis/application/services/sentiment_metrics_collector.py
"""
Sentiment Analysis Metrics Collection Service - Single Responsibility Principle
Extracted from BaseSentimentAnalysisTemplate God Class (517 lines)
Handles sentiment analysis metrics, quality assessment, and emotion extraction
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.sentiment_analysis.infrastructure.templates.sentiment_templates import SentimentInput, SentimentLabel
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysis
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("sentiment_metrics")


class SentimentMetricsCollector:
    """
    Sentiment metrics collection with Single Responsibility:
    Collect and analyze sentiment processing metrics, quality scores, and emotional indicators
    """
    
    def __init__(self):
        self.processing_history: List[Dict[str, Any]] = []
        self.quality_thresholds = {
            "min_confidence": 0.6,
            "min_text_length": 10,
            "max_processing_time": 30.0,
            "min_emotional_intensity": 0.3
        }
        
        # Emotion detection keywords
        self.emotion_keywords = {
            "joy": ["happy", "joy", "excited", "thrilled", "delighted", "cheerful", "elated"],
            "anger": ["angry", "mad", "furious", "irritated", "annoyed", "rage", "outraged"],
            "sadness": ["sad", "depressed", "disappointed", "grief", "sorrow", "melancholy"],
            "fear": ["afraid", "scared", "worried", "anxious", "nervous", "terrified", "panic"],
            "surprise": ["surprised", "amazed", "shocked", "astonished", "stunned", "bewildered"],
            "disgust": ["disgusted", "revolted", "repulsed", "nauseated", "appalled"],
            "trust": ["trust", "confident", "reliable", "faithful", "secure", "believe"],
            "anticipation": ["excited", "eager", "hopeful", "optimistic", "expectant"]
        }
    
    def start_analysis_metrics(self, input_data: SentimentInput, options: Dict[str, Any]) -> str:
        """
        Start metrics collection for sentiment analysis
        Returns metrics session ID
        """
        session_id = f"sentiment_{int(time.time())}_{hash(input_data.text) % 1000}"
        
        metrics_session = {
            "session_id": session_id,
            "language": input_data.language,
            "granularity": input_data.granularity.value,
            "text_length": len(input_data.text),
            "aspects_count": len(input_data.aspects) if input_data.aspects else 0,
            "start_time": datetime.utcnow(),
            "start_timestamp": time.time(),
            "options": options.copy(),
            "status": "started"
        }
        
        self.processing_history.append(metrics_session)
        
        logger.info(f"Started sentiment analysis metrics: {session_id}")
        return session_id
    
    def record_analysis_completed(
        self, 
        session_id: str, 
        result: SentimentAnalysis, 
        input_data: SentimentInput
    ) -> Dict[str, Any]:
        """
        Record completion metrics and assess quality
        Returns comprehensive metrics report
        """
        
        # Find the session
        session = self._find_session(session_id)
        if not session:
            logger.warning(f"Sentiment metrics session not found: {session_id}")
            return {}
        
        # Calculate processing metrics
        end_time = datetime.utcnow()
        end_timestamp = time.time()
        processing_duration = end_timestamp - session["start_timestamp"]
        
        # Update session with completion data
        session.update({
            "end_time": end_time,
            "end_timestamp": end_timestamp,
            "processing_duration": processing_duration,
            "status": "completed",
            "result": result
        })
        
        # Calculate performance metrics
        performance_metrics = self._calculate_performance_metrics(session, result, input_data)
        
        # Assess quality metrics
        quality_metrics = self._assess_quality_metrics(session, result, input_data)
        
        # Extract emotions
        emotion_metrics = self._extract_emotions(result, input_data)
        
        # Calculate sentiment trends if applicable
        trend_metrics = self._calculate_sentiment_trends(result, input_data)
        
        # Create comprehensive report
        metrics_report = {
            "session_id": session_id,
            "language": session["language"],
            "granularity": session["granularity"],
            "processing_duration": processing_duration,
            "performance": performance_metrics,
            "quality": quality_metrics,
            "emotions": emotion_metrics,
            "trends": trend_metrics,
            "overall_score": self._calculate_overall_score(performance_metrics, quality_metrics),
            "timestamp": end_time.isoformat()
        }
        
        session["metrics_report"] = metrics_report
        
        logger.info(f"Sentiment analysis metrics completed: {session_id}")
        logger.info(f"Processing time: {processing_duration:.2f}s")
        logger.info(f"Overall score: {metrics_report['overall_score']:.2f}")
        
        return metrics_report
    
    def record_analysis_failed(self, session_id: str, error: str) -> Dict[str, Any]:
        """Record analysis failure metrics"""
        
        session = self._find_session(session_id)
        if not session:
            return {}
        
        end_timestamp = time.time()
        processing_duration = end_timestamp - session["start_timestamp"]
        
        session.update({
            "end_time": datetime.utcnow(),
            "end_timestamp": end_timestamp,
            "processing_duration": processing_duration,
            "status": "failed",
            "error": error
        })
        
        failure_report = {
            "session_id": session_id,
            "language": session["language"],
            "processing_duration": processing_duration,
            "status": "failed",
            "error": error,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        session["failure_report"] = failure_report
        
        logger.error(f"Sentiment analysis failed: {session_id} - {error}")
        return failure_report
    
    def _calculate_performance_metrics(
        self, 
        session: Dict[str, Any], 
        result: SentimentAnalysis, 
        input_data: SentimentInput
    ) -> Dict[str, Any]:
        """Calculate performance-related metrics"""
        
        processing_duration = session["processing_duration"]
        text_length = session["text_length"]
        
        # Throughput metrics
        chars_per_second = text_length / max(processing_duration, 0.001)
        
        # Efficiency metrics
        time_efficiency = self._assess_time_efficiency(processing_duration, session["granularity"])
        
        return {
            "processing_duration": processing_duration,
            "chars_per_second": chars_per_second,
            "time_efficiency": time_efficiency,
            "text_length": text_length,
            "meets_time_threshold": processing_duration <= self.quality_thresholds["max_processing_time"]
        }
    
    def _assess_quality_metrics(
        self, 
        session: Dict[str, Any], 
        result: SentimentAnalysis, 
        input_data: SentimentInput
    ) -> Dict[str, Any]:
        """Assess quality-related metrics"""
        
        quality_metrics = {
            "confidence": result.confidence,
            "sentiment": result.sentiment.value,
            "scores_distribution": result.scores
        }
        
        # Confidence quality assessment
        confidence_quality = self._assess_confidence_quality(result.confidence)
        quality_metrics["confidence_quality"] = confidence_quality
        
        # Text length impact on quality
        text_quality = self._assess_text_length_quality(len(input_data.text))
        quality_metrics["text_length_quality"] = text_quality
        
        # Score distribution analysis
        score_analysis = self._analyze_score_distribution(result.scores)
        quality_metrics["score_analysis"] = score_analysis
        
        # Overall quality score
        overall_quality = (confidence_quality + text_quality + score_analysis["balance_score"]) / 3
        quality_metrics["overall_quality"] = overall_quality
        
        return quality_metrics
    
    def _extract_emotions(self, result: SentimentAnalysis, input_data: SentimentInput) -> Dict[str, Any]:
        """Extract emotional indicators from analyzed text"""
        
        text_lower = input_data.text.lower()
        emotion_scores = {}
        emotion_indicators = {}
        
        for emotion, keywords in self.emotion_keywords.items():
            # Count keyword matches
            matches = []
            for keyword in keywords:
                if keyword in text_lower:
                    matches.append(keyword)
            
            # Calculate emotion intensity
            intensity = len(matches) / max(len(text_lower.split()), 1)
            emotion_scores[emotion] = round(intensity, 3)
            
            if matches:
                emotion_indicators[emotion] = matches
        
        # Find dominant emotions
        dominant_emotions = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)[:3]
        dominant_emotions = [(emotion, score) for emotion, score in dominant_emotions if score > 0]
        
        return {
            "emotion_scores": emotion_scores,
            "emotion_indicators": emotion_indicators,
            "dominant_emotions": dominant_emotions,
            "emotional_intensity": max(emotion_scores.values()) if emotion_scores else 0.0,
            "emotional_diversity": len([e for e in emotion_scores.values() if e > 0])
        }
    
    def _calculate_sentiment_trends(self, result: SentimentAnalysis, input_data: SentimentInput) -> Dict[str, Any]:
        """Calculate sentiment trends if sentence-level analysis is available"""
        
        if not hasattr(result, 'sentence_sentiments') or not result.sentence_sentiments:
            return {"trend_available": False}
        
        sentence_sentiments = result.sentence_sentiments
        sentiment_sequence = [s["sentiment"].value for s in sentence_sentiments]
        
        # Analyze sentiment progression
        positive_trend = 0
        negative_trend = 0
        neutral_stable = 0
        
        for i in range(1, len(sentiment_sequence)):
            prev_sentiment = sentiment_sequence[i-1]
            curr_sentiment = sentiment_sequence[i]
            
            if prev_sentiment == "negative" and curr_sentiment == "positive":
                positive_trend += 1
            elif prev_sentiment == "positive" and curr_sentiment == "negative":
                negative_trend += 1
            elif prev_sentiment == "neutral" and curr_sentiment == "neutral":
                neutral_stable += 1
        
        total_transitions = len(sentiment_sequence) - 1
        
        return {
            "trend_available": True,
            "total_sentences": len(sentiment_sequence),
            "positive_transitions": positive_trend,
            "negative_transitions": negative_trend,
            "neutral_stability": neutral_stable,
            "sentiment_volatility": (positive_trend + negative_trend) / max(total_transitions, 1),
            "overall_trend": self._determine_overall_trend(sentiment_sequence)
        }
    
    def _determine_overall_trend(self, sentiment_sequence: List[str]) -> str:
        """Determine overall sentiment trend direction"""
        
        if len(sentiment_sequence) < 3:
            return "insufficient_data"
        
        # Compare first third with last third
        first_third = sentiment_sequence[:len(sentiment_sequence)//3]
        last_third = sentiment_sequence[-len(sentiment_sequence)//3:]
        
        first_positive = first_third.count("positive")
        last_positive = last_third.count("positive")
        
        first_negative = first_third.count("negative")
        last_negative = last_third.count("negative")
        
        if last_positive > first_positive and last_negative < first_negative:
            return "improving"
        elif last_positive < first_positive and last_negative > first_negative:
            return "declining"
        else:
            return "stable"
    
    def _assess_confidence_quality(self, confidence: float) -> float:
        """Assess quality based on confidence score"""
        
        if confidence >= 0.9:
            return 1.0  # Excellent confidence
        elif confidence >= 0.7:
            return 0.8  # Good confidence
        elif confidence >= 0.5:
            return 0.6  # Moderate confidence
        else:
            return 0.3  # Low confidence
    
    def _assess_text_length_quality(self, text_length: int) -> float:
        """Assess quality based on text length"""
        
        if text_length < 10:
            return 0.3  # Too short
        elif text_length < 50:
            return 0.6  # Short but workable
        elif text_length < 500:
            return 1.0  # Ideal length
        elif text_length < 2000:
            return 0.9  # Long but good
        else:
            return 0.7  # Very long, may be noisy
    
    def _analyze_score_distribution(self, scores: Dict[str, float]) -> Dict[str, Any]:
        """Analyze sentiment score distribution"""
        
        # Calculate score balance
        score_values = list(scores.values())
        max_score = max(score_values)
        min_score = min(score_values)
        score_range = max_score - min_score
        
        # Balance score (lower is more balanced)
        balance_score = 1.0 - (score_range / max(max_score, 0.001))
        
        # Determine clarity (how clear the sentiment is)
        clarity = max_score  # Higher max score means clearer sentiment
        
        return {
            "balance_score": balance_score,
            "clarity": clarity,
            "score_range": score_range,
            "dominant_score": max_score,
            "is_balanced": score_range < 0.3  # Scores are close to each other
        }
    
    def _assess_time_efficiency(self, duration: float, granularity: str) -> float:
        """Assess time efficiency based on analysis type"""
        
        # Expected processing times by granularity (in seconds)
        expected_times = {
            "document": 1.0,
            "sentence": 2.0,
            "aspect": 3.0
        }
        
        expected_time = expected_times.get(granularity, 2.0)
        
        if duration <= expected_time:
            return 1.0
        elif duration <= expected_time * 2:
            return 0.8
        elif duration <= expected_time * 3:
            return 0.6
        else:
            return 0.4
    
    def _calculate_overall_score(self, performance: Dict[str, Any], quality: Dict[str, Any]) -> float:
        """Calculate overall processing score"""
        
        # Weight: 30% performance, 70% quality (quality is more important for sentiment analysis)
        performance_score = performance.get("time_efficiency", 0.5)
        quality_score = quality.get("overall_quality", 0.5)
        
        overall_score = (performance_score * 0.3) + (quality_score * 0.7)
        return round(overall_score, 3)
    
    def _find_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Find metrics session by ID"""
        for session in self.processing_history:
            if session["session_id"] == session_id:
                return session
        return None
    
    def get_metrics_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get summary of recent sentiment analysis metrics"""
        
        recent_sessions = self.processing_history[-limit:]
        completed_sessions = [s for s in recent_sessions if s["status"] == "completed"]
        failed_sessions = [s for s in recent_sessions if s["status"] == "failed"]
        
        if not recent_sessions:
            return {"message": "No sentiment analysis history available"}
        
        # Calculate averages
        avg_duration = 0
        avg_confidence = 0
        avg_score = 0
        
        if completed_sessions:
            avg_duration = sum(s["processing_duration"] for s in completed_sessions) / len(completed_sessions)
            avg_confidence = sum(s["result"].confidence for s in completed_sessions) / len(completed_sessions)
            avg_score = sum(s.get("metrics_report", {}).get("overall_score", 0) for s in completed_sessions) / len(completed_sessions)
        
        return {
            "total_sessions": len(recent_sessions),
            "completed_sessions": len(completed_sessions),
            "failed_sessions": len(failed_sessions),
            "success_rate": len(completed_sessions) / len(recent_sessions) if recent_sessions else 0,
            "average_processing_duration": avg_duration,
            "average_confidence": avg_confidence,
            "average_quality_score": avg_score,
            "languages_breakdown": self._get_languages_breakdown(recent_sessions),
            "granularity_breakdown": self._get_granularity_breakdown(recent_sessions)
        }
    
    def _get_languages_breakdown(self, sessions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of languages in sessions"""
        breakdown = {}
        for session in sessions:
            language = session["language"]
            breakdown[language] = breakdown.get(language, 0) + 1
        return breakdown
    
    def _get_granularity_breakdown(self, sessions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of granularities in sessions"""
        breakdown = {}
        for session in sessions:
            granularity = session["granularity"]
            breakdown[granularity] = breakdown.get(granularity, 0) + 1
        return breakdown


# Default instance
sentiment_metrics_collector = SentimentMetricsCollector()