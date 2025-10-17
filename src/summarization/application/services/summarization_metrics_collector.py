# src/summarization/application/services/summarization_metrics_collector.py
"""
Summarization Metrics Collection Service - Single Responsibility Principle
Extracted from BaseSummarizationTemplate God Class (514 lines)
Handles summarization metrics, quality assessment, and readability analysis
"""

import time
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.summarization.infrastructure.templates.summarization_templates import SummarizationInput, SummaryType
from src.summarization.domain.summary import Summary
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("summarization_metrics")


class SummarizationMetricsCollector:
    """
    Summarization metrics collection with Single Responsibility:
    Collect and analyze summarization processing metrics and quality scores
    """
    
    def __init__(self):
        self.processing_history: List[Dict[str, Any]] = []
        self.quality_thresholds = {
            "min_compression_ratio": 0.1,
            "max_compression_ratio": 0.8,
            "min_readability_score": 30,
            "max_processing_time": 60.0,
            "min_coherence_score": 0.6
        }
    
    def start_summarization_metrics(self, input_data: SummarizationInput, options: Dict[str, Any]) -> str:
        """
        Start metrics collection for summarization
        Returns metrics session ID
        """
        session_id = f"summary_{int(time.time())}_{hash(input_data.text) % 1000}"
        
        metrics_session = {
            "session_id": session_id,
            "language": input_data.language,
            "summary_type": input_data.summary_type.value,
            "summary_length": input_data.summary_length.value,
            "original_text_length": len(input_data.text),
            "original_word_count": len(input_data.text.split()),
            "start_time": datetime.utcnow(),
            "start_timestamp": time.time(),
            "options": options.copy(),
            "status": "started"
        }
        
        self.processing_history.append(metrics_session)
        
        logger.info(f"Started summarization metrics: {session_id}")
        return session_id
    
    def record_summarization_completed(
        self, 
        session_id: str, 
        result: Summary, 
        input_data: SummarizationInput
    ) -> Dict[str, Any]:
        """
        Record completion metrics and assess quality
        Returns comprehensive metrics report
        """
        
        # Find the session
        session = self._find_session(session_id)
        if not session:
            logger.warning(f"Summarization metrics session not found: {session_id}")
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
        
        # Calculate comprehensive metrics
        compression_metrics = self._calculate_compression_metrics(session, result, input_data)
        quality_metrics = self._assess_quality_metrics(session, result, input_data)
        readability_metrics = self._assess_readability_metrics(result)
        coherence_metrics = self._assess_coherence_metrics(result, input_data)
        
        # Create comprehensive report
        metrics_report = {
            "session_id": session_id,
            "summary_type": session["summary_type"],
            "summary_length": session["summary_length"],
            "processing_duration": processing_duration,
            "compression": compression_metrics,
            "quality": quality_metrics,
            "readability": readability_metrics,
            "coherence": coherence_metrics,
            "overall_score": self._calculate_overall_score(compression_metrics, quality_metrics, readability_metrics),
            "timestamp": end_time.isoformat()
        }
        
        session["metrics_report"] = metrics_report
        
        logger.info(f"Summarization metrics completed: {session_id}")
        logger.info(f"Processing time: {processing_duration:.2f}s")
        logger.info(f"Compression ratio: {compression_metrics['compression_ratio']:.2f}")
        logger.info(f"Overall score: {metrics_report['overall_score']:.2f}")
        
        return metrics_report
    
    def _calculate_compression_metrics(
        self, 
        session: Dict[str, Any], 
        result: Summary, 
        input_data: SummarizationInput
    ) -> Dict[str, Any]:
        """Calculate compression-related metrics"""
        
        original_words = len(input_data.text.split())
        summary_words = len(result.text.split())
        original_chars = len(input_data.text)
        summary_chars = len(result.text)
        
        compression_ratio = summary_words / max(original_words, 1)
        char_compression_ratio = summary_chars / max(original_chars, 1)
        
        return {
            "original_word_count": original_words,
            "summary_word_count": summary_words,
            "word_reduction": original_words - summary_words,
            "compression_ratio": round(compression_ratio, 3),
            "char_compression_ratio": round(char_compression_ratio, 3),
            "compression_efficiency": self._assess_compression_efficiency(compression_ratio, input_data.summary_length),
            "meets_length_target": self._meets_length_target(compression_ratio, input_data.summary_length)
        }
    
    def _assess_quality_metrics(
        self, 
        session: Dict[str, Any], 
        result: Summary, 
        input_data: SummarizationInput
    ) -> Dict[str, Any]:
        """Assess quality-related metrics"""
        
        # Information preservation score
        info_preservation = self._calculate_information_preservation(result, input_data)
        
        # Summary completeness
        completeness = self._assess_summary_completeness(result, input_data)
        
        # Language quality
        language_quality = self._assess_language_quality(result.text)
        
        return {
            "information_preservation": info_preservation,
            "completeness": completeness,
            "language_quality": language_quality,
            "summary_type_appropriateness": self._assess_type_appropriateness(result, input_data),
            "factual_consistency": self._assess_factual_consistency(result, input_data)
        }
    
    def _assess_readability_metrics(self, result: Summary) -> Dict[str, Any]:
        """Assess readability metrics"""
        
        text = result.text
        sentences = self._split_sentences(text)
        words = text.split()
        
        # Basic readability calculations
        avg_sentence_length = len(words) / max(len(sentences), 1)
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        
        # Simple readability score (Flesch-like approximation)
        readability_score = 206.835 - (1.015 * avg_sentence_length) - (84.6 * avg_word_length / 4.7)
        readability_score = max(0, min(100, readability_score))  # Clamp to 0-100
        
        return {
            "sentence_count": len(sentences),
            "word_count": len(words),
            "avg_sentence_length": round(avg_sentence_length, 1),
            "avg_word_length": round(avg_word_length, 1),
            "readability_score": round(readability_score, 1),
            "readability_level": self._categorize_readability(readability_score)
        }
    
    def _assess_coherence_metrics(self, result: Summary, input_data: SummarizationInput) -> Dict[str, Any]:
        """Assess coherence and flow metrics"""
        
        sentences = self._split_sentences(result.text)
        
        # Sentence transition quality (simplified)
        transition_score = self._calculate_transition_score(sentences)
        
        # Topic consistency
        topic_consistency = self._assess_topic_consistency(result, input_data)
        
        # Logical flow
        logical_flow = self._assess_logical_flow(sentences)
        
        return {
            "sentence_transitions": transition_score,
            "topic_consistency": topic_consistency,
            "logical_flow": logical_flow,
            "overall_coherence": round((transition_score + topic_consistency + logical_flow) / 3, 3)
        }
    
    def _assess_compression_efficiency(self, compression_ratio: float, summary_length) -> float:
        """Assess if compression ratio is appropriate for the target length"""
        
        # Target compression ratios by length
        target_ratios = {
            "short": 0.15,
            "medium": 0.30,
            "long": 0.50,
            "custom": 0.30  # default
        }
        
        target = target_ratios.get(summary_length.value, 0.30)
        
        # Calculate efficiency based on how close we are to target
        deviation = abs(compression_ratio - target)
        efficiency = max(0, 1 - (deviation * 2))  # Penalize large deviations
        
        return round(efficiency, 3)
    
    def _calculate_information_preservation(self, result: Summary, input_data: SummarizationInput) -> float:
        """Calculate how well information is preserved (simplified)"""
        
        # Simple keyword overlap approach
        original_words = set(word.lower() for word in input_data.text.split() if len(word) > 3)
        summary_words = set(word.lower() for word in result.text.split() if len(word) > 3)
        
        if not original_words:
            return 0.0
        
        overlap = len(original_words.intersection(summary_words))
        preservation_score = overlap / len(original_words)
        
        return round(preservation_score, 3)
    
    def _categorize_readability(self, score: float) -> str:
        """Categorize readability score"""
        if score >= 90:
            return "very_easy"
        elif score >= 80:
            return "easy"
        elif score >= 70:
            return "fairly_easy"
        elif score >= 60:
            return "standard"
        elif score >= 50:
            return "fairly_difficult"
        elif score >= 30:
            return "difficult"
        else:
            return "very_difficult"
    
    def _calculate_overall_score(
        self, 
        compression: Dict[str, Any], 
        quality: Dict[str, Any], 
        readability: Dict[str, Any]
    ) -> float:
        """Calculate overall summarization score"""
        
        # Weighted combination of different aspects
        compression_score = compression.get("compression_efficiency", 0.5)
        quality_score = (
            quality.get("information_preservation", 0.5) + 
            quality.get("completeness", 0.5) + 
            quality.get("language_quality", 0.5)
        ) / 3
        
        readability_score = min(1.0, readability.get("readability_score", 50) / 100)
        
        # Weight: 30% compression, 50% quality, 20% readability
        overall_score = (
            compression_score * 0.3 + 
            quality_score * 0.5 + 
            readability_score * 0.2
        )
        
        return round(overall_score, 3)
    
    def get_metrics_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get summary of recent summarization metrics"""
        
        recent_sessions = self.processing_history[-limit:]
        completed_sessions = [s for s in recent_sessions if s["status"] == "completed"]
        
        if not recent_sessions:
            return {"message": "No summarization history available"}
        
        # Calculate averages
        if completed_sessions:
            avg_duration = sum(s["processing_duration"] for s in completed_sessions) / len(completed_sessions)
            avg_compression = sum(
                s.get("metrics_report", {}).get("compression", {}).get("compression_ratio", 0) 
                for s in completed_sessions
            ) / len(completed_sessions)
            avg_score = sum(
                s.get("metrics_report", {}).get("overall_score", 0) 
                for s in completed_sessions
            ) / len(completed_sessions)
        else:
            avg_duration = avg_compression = avg_score = 0
        
        return {
            "total_sessions": len(recent_sessions),
            "completed_sessions": len(completed_sessions),
            "success_rate": len(completed_sessions) / len(recent_sessions) if recent_sessions else 0,
            "average_processing_duration": avg_duration,
            "average_compression_ratio": avg_compression,
            "average_quality_score": avg_score,
            "summary_types_breakdown": self._get_types_breakdown(recent_sessions),
            "languages_breakdown": self._get_languages_breakdown(recent_sessions)
        }
    
    def _find_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Find metrics session by ID"""
        for session in self.processing_history:
            if session["session_id"] == session_id:
                return session
        return None


# Default instance
summarization_metrics_collector = SummarizationMetricsCollector()