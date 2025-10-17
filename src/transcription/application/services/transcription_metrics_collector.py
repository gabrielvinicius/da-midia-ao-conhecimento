# src/transcription/application/services/transcription_metrics_collector.py
"""
Transcription Metrics Collection Service - Single Responsibility Principle
Extracted from BaseTranscriptionTemplate God Class (421 lines)
Handles transcription metrics, quality assessment, and accuracy analysis
"""

import time
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.transcription.infrastructure.templates.transcription_templates import TranscriptionInput, AudioFormat
from src.transcription.domain.transcription import Transcription
from src.shared.infrastructure.logging_config import get_logger

logger = get_logger("transcription_metrics")


class TranscriptionMetricsCollector:
    """
    Transcription metrics collection with Single Responsibility:
    Collect and analyze transcription processing metrics and accuracy scores
    """
    
    def __init__(self):
        self.processing_history: List[Dict[str, Any]] = []
        self.quality_thresholds = {
            "min_confidence": 0.7,
            "min_audio_duration": 0.5,
            "max_processing_time": 120.0,  # 2 minutes
            "min_transcription_length": 5,
            "max_error_rate": 0.15
        }
    
    def start_transcription_metrics(self, input_data: TranscriptionInput, options: Dict[str, Any]) -> str:
        """
        Start metrics collection for transcription
        Returns metrics session ID
        """
        session_id = f"transcription_{int(time.time())}_{hash(input_data.audio_data) % 1000}"
        
        metrics_session = {
            "session_id": session_id,
            "language": input_data.language,
            "audio_format": input_data.audio_format.value,
            "audio_size": len(input_data.audio_data),
            "sample_rate": input_data.sample_rate,
            "channels": input_data.channels,
            "start_time": datetime.utcnow(),
            "start_timestamp": time.time(),
            "options": options.copy(),
            "status": "started"
        }
        
        self.processing_history.append(metrics_session)
        
        logger.info(f"Started transcription metrics: {session_id}")
        return session_id
    
    def record_transcription_completed(
        self, 
        session_id: str, 
        result: Transcription, 
        input_data: TranscriptionInput
    ) -> Dict[str, Any]:
        """
        Record completion metrics and assess quality
        Returns comprehensive metrics report
        """
        
        # Find the session
        session = self._find_session(session_id)
        if not session:
            logger.warning(f"Transcription metrics session not found: {session_id}")
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
        performance_metrics = self._calculate_performance_metrics(session, result, input_data)
        accuracy_metrics = self._assess_accuracy_metrics(session, result, input_data)
        quality_metrics = self._assess_quality_metrics(session, result, input_data)
        audio_metrics = self._analyze_audio_metrics(session, input_data)
        
        # Create comprehensive report
        metrics_report = {
            "session_id": session_id,
            "language": session["language"],
            "audio_format": session["audio_format"],
            "processing_duration": processing_duration,
            "performance": performance_metrics,
            "accuracy": accuracy_metrics,
            "quality": quality_metrics,
            "audio_analysis": audio_metrics,
            "overall_score": self._calculate_overall_score(performance_metrics, accuracy_metrics, quality_metrics),
            "timestamp": end_time.isoformat()
        }
        
        session["metrics_report"] = metrics_report
        
        logger.info(f"Transcription metrics completed: {session_id}")
        logger.info(f"Processing time: {processing_duration:.2f}s")
        logger.info(f"Confidence: {result.confidence:.2f}")
        logger.info(f"Overall score: {metrics_report['overall_score']:.2f}")
        
        return metrics_report
    
    def record_transcription_failed(self, session_id: str, error: str) -> Dict[str, Any]:
        """Record transcription failure metrics"""
        
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
        
        logger.error(f"Transcription failed: {session_id} - {error}")
        return failure_report
    
    def _calculate_performance_metrics(
        self, 
        session: Dict[str, Any], 
        result: Transcription, 
        input_data: TranscriptionInput
    ) -> Dict[str, Any]:
        """Calculate performance-related metrics"""
        
        processing_duration = session["processing_duration"]
        audio_size = session["audio_size"]
        
        # Estimate audio duration
        estimated_duration = self._estimate_audio_duration(input_data)
        
        # Calculate throughput
        audio_mb = audio_size / (1024 * 1024)
        throughput_mbps = audio_mb / max(processing_duration, 0.001)
        
        # Real-time factor (processing_time / audio_duration)
        rtf = processing_duration / max(estimated_duration, 0.001)
        
        # Time efficiency assessment
        time_efficiency = self._assess_time_efficiency(processing_duration, estimated_duration)
        
        return {
            "processing_duration": processing_duration,
            "estimated_audio_duration": estimated_duration,
            "throughput_mbps": throughput_mbps,
            "real_time_factor": rtf,
            "time_efficiency": time_efficiency,
            "audio_size_mb": audio_mb,
            "meets_time_threshold": processing_duration <= self.quality_thresholds["max_processing_time"],
            "is_real_time": rtf <= 1.0
        }
    
    def _assess_accuracy_metrics(
        self, 
        session: Dict[str, Any], 
        result: Transcription, 
        input_data: TranscriptionInput
    ) -> Dict[str, Any]:
        """Assess accuracy-related metrics"""
        
        transcription_text = result.text
        confidence = result.confidence
        
        # Text analysis
        word_count = len(transcription_text.split())
        char_count = len(transcription_text)
        
        # Confidence analysis
        confidence_category = self._categorize_confidence(confidence)
        
        # Language consistency check
        language_consistency = self._check_language_consistency(transcription_text, input_data.language)
        
        # Text quality indicators
        text_quality = self._assess_text_quality(transcription_text)
        
        return {
            "confidence": confidence,
            "confidence_category": confidence_category,
            "word_count": word_count,
            "character_count": char_count,
            "language_consistency": language_consistency,
            "text_quality": text_quality,
            "meets_confidence_threshold": confidence >= self.quality_thresholds["min_confidence"],
            "meets_length_threshold": word_count >= self.quality_thresholds["min_transcription_length"]
        }
    
    def _assess_quality_metrics(
        self, 
        session: Dict[str, Any], 
        result: Transcription, 
        input_data: TranscriptionInput
    ) -> Dict[str, Any]:
        """Assess overall quality metrics"""
        
        # Timestamp quality (if available)
        timestamp_quality = self._assess_timestamp_quality(result)
        
        # Speaker diarization quality (if available)
        speaker_quality = self._assess_speaker_quality(result)
        
        # Audio-text alignment quality
        alignment_quality = self._assess_alignment_quality(result, input_data)
        
        # Overall transcription completeness
        completeness = self._assess_completeness(result, input_data)
        
        return {
            "timestamp_quality": timestamp_quality,
            "speaker_quality": speaker_quality,
            "alignment_quality": alignment_quality,
            "completeness": completeness,
            "has_timestamps": hasattr(result, 'timestamps') and result.timestamps is not None,
            "has_speakers": hasattr(result, 'speakers') and result.speakers is not None
        }
    
    def _analyze_audio_metrics(self, session: Dict[str, Any], input_data: TranscriptionInput) -> Dict[str, Any]:
        """Analyze audio-specific metrics"""
        
        audio_size = session["audio_size"]
        estimated_duration = self._estimate_audio_duration(input_data)
        
        # Calculate estimated bitrate
        estimated_bitrate = (audio_size * 8) / max(estimated_duration, 0.001)
        
        # Audio quality indicators
        quality_indicators = {
            "format_optimal": input_data.audio_format in [AudioFormat.WAV, AudioFormat.FLAC],
            "sample_rate_optimal": input_data.sample_rate >= 16000,
            "channels_optimal": input_data.channels <= 2,
            "duration_optimal": 1.0 <= estimated_duration <= 1800,  # 1 second to 30 minutes
            "bitrate_adequate": estimated_bitrate >= 64000  # 64 kbps
        }
        
        audio_quality_score = sum(quality_indicators.values()) / len(quality_indicators)
        
        return {
            "estimated_bitrate": estimated_bitrate,
            "quality_indicators": quality_indicators,
            "audio_quality_score": audio_quality_score,
            "format": input_data.audio_format.value,
            "sample_rate": input_data.sample_rate,
            "channels": input_data.channels,
            "estimated_duration": estimated_duration
        }
    
    def _estimate_audio_duration(self, input_data: TranscriptionInput) -> float:
        """Estimate audio duration (simplified calculation)"""
        
        # Rough estimation based on format and size
        audio_size = len(input_data.audio_data)
        
        if input_data.audio_format == AudioFormat.WAV:
            # Uncompressed: bytes = sample_rate * channels * bit_depth/8 * duration
            bytes_per_second = input_data.sample_rate * input_data.channels * 2  # Assume 16-bit
            duration = (audio_size - 44) / bytes_per_second  # Subtract WAV header
        else:
            # Compressed formats: estimate based on typical bitrates
            typical_bitrates = {
                AudioFormat.MP3: 128000,
                AudioFormat.M4A: 128000,
                AudioFormat.OGG: 128000,
                AudioFormat.FLAC: 800000
            }
            bitrate = typical_bitrates.get(input_data.audio_format, 128000)
            duration = (audio_size * 8) / bitrate
        
        return max(0.1, min(duration, 7200))  # Between 0.1s and 2 hours
    
    def _categorize_confidence(self, confidence: float) -> str:
        """Categorize confidence score"""
        if confidence >= 0.95:
            return "excellent"
        elif confidence >= 0.85:
            return "high"
        elif confidence >= 0.70:
            return "medium"
        elif confidence >= 0.50:
            return "low"
        else:
            return "very_low"
    
    def _check_language_consistency(self, text: str, expected_language: str) -> float:
        """Check if transcribed text is consistent with expected language (simplified)"""
        
        # Simple heuristic based on character patterns
        if expected_language == "en":
            # English: mostly ASCII characters
            ascii_ratio = sum(1 for c in text if ord(c) < 128) / max(len(text), 1)
            return min(1.0, ascii_ratio + 0.2)
        elif expected_language in ["es", "fr", "it", "pt"]:
            # Romance languages: some accented characters
            return 0.85  # Assume good consistency
        elif expected_language in ["zh", "ja", "ko"]:
            # CJK languages: many non-ASCII characters
            non_ascii_ratio = sum(1 for c in text if ord(c) >= 128) / max(len(text), 1)
            return min(1.0, non_ascii_ratio + 0.3)
        else:
            return 0.8  # Default assumption
    
    def _assess_text_quality(self, text: str) -> Dict[str, Any]:
        """Assess transcribed text quality"""
        
        words = text.split()
        
        # Calculate various quality indicators
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        unique_words = len(set(word.lower() for word in words))
        repetition_ratio = 1.0 - (unique_words / max(len(words), 1))
        
        # Check for common transcription artifacts
        has_repeated_words = any(words[i] == words[i+1] for i in range(len(words)-1))
        has_incomplete_words = any(len(word) == 1 and word.isalpha() for word in words)
        
        quality_score = 1.0
        if repetition_ratio > 0.5:
            quality_score -= 0.3
        if has_repeated_words:
            quality_score -= 0.2
        if has_incomplete_words:
            quality_score -= 0.1
        
        return {
            "avg_word_length": avg_word_length,
            "unique_word_ratio": unique_words / max(len(words), 1),
            "repetition_ratio": repetition_ratio,
            "has_repeated_words": has_repeated_words,
            "has_incomplete_words": has_incomplete_words,
            "quality_score": max(0.0, quality_score)
        }
    
    def _assess_timestamp_quality(self, result: Transcription) -> Optional[Dict[str, Any]]:
        """Assess timestamp quality if available"""
        
        if not hasattr(result, 'timestamps') or not result.timestamps:
            return None
        
        timestamps = result.timestamps
        
        # Check timestamp consistency
        timing_issues = 0
        for i, ts in enumerate(timestamps):
            if ts['start'] >= ts['end']:
                timing_issues += 1
            if i > 0 and ts['start'] < timestamps[i-1]['end']:
                timing_issues += 1
        
        quality_score = 1.0 - (timing_issues / max(len(timestamps), 1))
        
        return {
            "total_timestamps": len(timestamps),
            "timing_issues": timing_issues,
            "quality_score": quality_score,
            "avg_confidence": sum(ts.get('confidence', 0) for ts in timestamps) / len(timestamps)
        }
    
    def _assess_speaker_quality(self, result: Transcription) -> Optional[Dict[str, Any]]:
        """Assess speaker diarization quality if available"""
        
        if not hasattr(result, 'speakers') or not result.speakers:
            return None
        
        speakers = result.speakers
        
        return {
            "speaker_count": len(speakers),
            "total_speaking_time": sum(s.get('end_time', 0) - s.get('start_time', 0) for s in speakers),
            "avg_segment_length": sum(s.get('end_time', 0) - s.get('start_time', 0) for s in speakers) / len(speakers)
        }
    
    def _assess_alignment_quality(self, result: Transcription, input_data: TranscriptionInput) -> float:
        """Assess audio-text alignment quality"""
        
        # Simple heuristic: longer transcriptions for longer audio should score higher
        estimated_duration = self._estimate_audio_duration(input_data)
        word_count = len(result.text.split())
        
        # Expect roughly 2-3 words per second for normal speech
        expected_words = estimated_duration * 2.5
        
        if expected_words > 0:
            alignment_score = min(1.0, word_count / expected_words)
            # Penalize if way too short or too long
            if alignment_score < 0.3 or alignment_score > 3.0:
                alignment_score *= 0.5
        else:
            alignment_score = 0.5
        
        return min(1.0, alignment_score)
    
    def _assess_completeness(self, result: Transcription, input_data: TranscriptionInput) -> float:
        """Assess transcription completeness"""
        
        # Combine various factors to assess completeness
        confidence_factor = result.confidence
        length_factor = min(1.0, len(result.text.split()) / 10)  # Normalize by expected minimum
        
        completeness = (confidence_factor + length_factor) / 2
        return completeness
    
    def _assess_time_efficiency(self, processing_time: float, audio_duration: float) -> float:
        """Assess time efficiency"""
        
        rtf = processing_time / max(audio_duration, 0.001)
        
        if rtf <= 0.5:  # Faster than real-time
            return 1.0
        elif rtf <= 1.0:  # Real-time
            return 0.8
        elif rtf <= 2.0:  # 2x real-time
            return 0.6
        else:  # Slower than 2x
            return 0.4
    
    def _calculate_overall_score(
        self, 
        performance: Dict[str, Any], 
        accuracy: Dict[str, Any], 
        quality: Dict[str, Any]
    ) -> float:
        """Calculate overall transcription score"""
        
        # Weighted combination: 20% performance, 50% accuracy, 30% quality
        performance_score = performance.get("time_efficiency", 0.5)
        accuracy_score = (
            accuracy.get("confidence", 0.5) + 
            accuracy.get("text_quality", {}).get("quality_score", 0.5) +
            accuracy.get("language_consistency", 0.5)
        ) / 3
        
        quality_score = (
            quality.get("completeness", 0.5) + 
            quality.get("alignment_quality", 0.5)
        ) / 2
        
        overall_score = (
            performance_score * 0.2 + 
            accuracy_score * 0.5 + 
            quality_score * 0.3
        )
        
        return round(overall_score, 3)
    
    def _find_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Find metrics session by ID"""
        for session in self.processing_history:
            if session["session_id"] == session_id:
                return session
        return None
    
    def get_metrics_summary(self, limit: int = 10) -> Dict[str, Any]:
        """Get summary of recent transcription metrics"""
        
        recent_sessions = self.processing_history[-limit:]
        completed_sessions = [s for s in recent_sessions if s["status"] == "completed"]
        failed_sessions = [s for s in recent_sessions if s["status"] == "failed"]
        
        if not recent_sessions:
            return {"message": "No transcription history available"}
        
        # Calculate averages
        if completed_sessions:
            avg_duration = sum(s["processing_duration"] for s in completed_sessions) / len(completed_sessions)
            avg_confidence = sum(s["result"].confidence for s in completed_sessions) / len(completed_sessions)
            avg_score = sum(s.get("metrics_report", {}).get("overall_score", 0) for s in completed_sessions) / len(completed_sessions)
        else:
            avg_duration = avg_confidence = avg_score = 0
        
        return {
            "total_sessions": len(recent_sessions),
            "completed_sessions": len(completed_sessions),
            "failed_sessions": len(failed_sessions),
            "success_rate": len(completed_sessions) / len(recent_sessions) if recent_sessions else 0,
            "average_processing_duration": avg_duration,
            "average_confidence": avg_confidence,
            "average_quality_score": avg_score,
            "languages_breakdown": self._get_languages_breakdown(recent_sessions),
            "formats_breakdown": self._get_formats_breakdown(recent_sessions)
        }
    
    def _get_languages_breakdown(self, sessions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of languages in sessions"""
        breakdown = {}
        for session in sessions:
            language = session["language"]
            breakdown[language] = breakdown.get(language, 0) + 1
        return breakdown
    
    def _get_formats_breakdown(self, sessions: List[Dict[str, Any]]) -> Dict[str, int]:
        """Get breakdown of audio formats in sessions"""
        breakdown = {}
        for session in sessions:
            audio_format = session["audio_format"]
            breakdown[audio_format] = breakdown.get(audio_format, 0) + 1
        return breakdown


# Default instance
transcription_metrics_collector = TranscriptionMetricsCollector()