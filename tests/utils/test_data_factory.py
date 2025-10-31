# tests/utils/test_data_factory.py
"""
Factory for creating realistic test data objects.
Provides consistent, valid test data for all domains.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import uuid4
import random

from src.auth.domain.user import User, UserRole
from src.media_management.domain.media import Media, MediaType, MediaStatus
from src.transcription.domain.transcription import Transcription, TranscriptionStatus
from src.summarization.domain.summary import Summary
from src.sentiment_analysis.domain.sentiment_analysis import SentimentAnalysisResult
from src.topic_modeling.domain.topic_modeling import TopicModelingResult


class TestDataFactory:
    """Factory for creating test data objects with realistic values."""
    
    def __init__(self):
        self._counter = 0
    
    def _unique_id(self) -> str:
        """Generate a unique ID for test objects."""
        self._counter += 1
        return f"test_{self._counter}_{uuid4().hex[:8]}"
    
    def _random_email(self) -> str:
        """Generate a random email for testing."""
        domains = ["example.com", "test.org", "demo.net"]
        return f"user_{self._unique_id()}@{random.choice(domains)}"
    
    # ============================================================================
    # AUTH DOMAIN
    # ============================================================================
    
    def create_user(
        self,
        email: Optional[str] = None,
        password_hash: Optional[str] = None,
        role: UserRole = UserRole.USER,
        is_active: bool = True,
        **kwargs
    ) -> User:
        """Create a test User entity."""
        return User(
            id=self._unique_id(),
            email=email or self._random_email(),
            password_hash=password_hash or "hashed_password_123",
            role=role,
            is_active=is_active,
            **kwargs
        )
    
    def create_admin_user(self, **kwargs) -> User:
        """Create a test admin User entity."""
        return self.create_user(role=UserRole.ADMIN, **kwargs)
    
    def create_user_data(self, **kwargs) -> Dict[str, Any]:
        """Create user registration/update data."""
        return {
            "email": self._random_email(),
            "password": "SecurePassword123!",
            "role": "USER",
            **kwargs
        }
    
    # ============================================================================
    # MEDIA MANAGEMENT DOMAIN
    # ============================================================================
    
    def create_media(
        self,
        user_id: Optional[str] = None,
        media_type: MediaType = MediaType.AUDIO,
        status: MediaStatus = MediaStatus.UPLOADED,
        **kwargs
    ) -> Media:
        """Create a test Media entity."""
        media_id = self._unique_id()
        filename = f"test_{media_type.value}_{media_id}"
        
        if media_type == MediaType.AUDIO:
            filename += ".mp3"
        elif media_type == MediaType.VIDEO:
            filename += ".mp4"
        else:
            filename += ".txt"
            
        return Media(
            id=media_id,
            user_id=user_id or self._unique_id(),
            original_file_path=f"/uploads/{filename}",
            filename=filename,
            media_type=media_type,
            status=status,
            file_size=random.randint(1024, 1024*1024),  # 1KB to 1MB
            duration=random.randint(30, 3600) if media_type in [MediaType.AUDIO, MediaType.VIDEO] else None,
            created_at=datetime.utcnow(),
            **kwargs
        )
    
    def create_audio_media(self, **kwargs) -> Media:
        """Create a test audio Media entity."""
        return self.create_media(media_type=MediaType.AUDIO, **kwargs)
    
    def create_video_media(self, **kwargs) -> Media:
        """Create a test video Media entity."""
        return self.create_media(media_type=MediaType.VIDEO, **kwargs)
    
    def create_upload_data(self, media_type: MediaType = MediaType.AUDIO) -> Dict[str, Any]:
        """Create file upload data for testing."""
        if media_type == MediaType.AUDIO:
            content = b"fake_audio_content"
            filename = f"test_audio_{self._unique_id()}.mp3"
            content_type = "audio/mp3"
        elif media_type == MediaType.VIDEO:
            content = b"fake_video_content"
            filename = f"test_video_{self._unique_id()}.mp4"
            content_type = "video/mp4"
        else:
            content = b"fake_text_content"
            filename = f"test_text_{self._unique_id()}.txt"
            content_type = "text/plain"
            
        return {
            "file": content,
            "filename": filename,
            "content_type": content_type,
            "storage_provider": "local"
        }
    
    # ============================================================================
    # TRANSCRIPTION DOMAIN
    # ============================================================================
    
    def create_transcription(
        self,
        media_id: Optional[str] = None,
        status: TranscriptionStatus = TranscriptionStatus.COMPLETED,
        **kwargs
    ) -> Transcription:
        """Create a test Transcription entity."""
        sample_texts = [
            "This is a sample transcription of an audio file.",
            "Hello world, this is a test transcription.",
            "The quick brown fox jumps over the lazy dog.",
            "This is a longer transcription with multiple sentences. It contains various words and phrases."
        ]
        
        sample_segments = [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "This is a sample",
                "speaker": "Speaker 1",
                "confidence": 0.95
            },
            {
                "start": 2.5,
                "end": 5.0,
                "text": "transcription of an audio file.",
                "speaker": "Speaker 1", 
                "confidence": 0.89
            }
        ]
        
        return Transcription(
            id=self._unique_id(),
            media_id=media_id or self._unique_id(),
            text=random.choice(sample_texts),
            language="en",
            provider="whisper",
            status=status,
            confidence_score=round(random.uniform(0.8, 0.99), 2),
            segments=sample_segments,
            speakers=["Speaker 1", "Speaker 2"],
            processing_time=round(random.uniform(1.0, 10.0), 2),
            created_at=datetime.utcnow(),
            **kwargs
        )
    
    def create_transcription_command_data(self, **kwargs) -> Dict[str, Any]:
        """Create transcription command data."""
        return {
            "media_id": self._unique_id(),
            "file_path": f"/uploads/audio_{self._unique_id()}.mp3",
            "storage_provider": "local",
            "transcription_provider": "whisper",
            "language": "en",
            **kwargs
        }
    
    # ============================================================================
    # SUMMARIZATION DOMAIN
    # ============================================================================
    
    def create_summary(
        self,
        media_id: Optional[str] = None,
        text_content: Optional[str] = None,
        **kwargs
    ) -> Summary:
        """Create a test Summary entity."""
        sample_summaries = [
            "This is a brief summary of the main topics discussed.",
            "Key points: technology trends, market analysis, and future predictions.",
            "The conversation covered multiple aspects of software development and best practices."
        ]
        
        if text_content is None:
            text_content = random.choice(sample_summaries)
            
        return Summary(
            id=self._unique_id(),
            media_id=media_id or self._unique_id(),
            text=text_content,
            strategy="extractive",
            provider="huggingface",
            bullet_points=[
                "First key point from the summary",
                "Second important insight",
                "Third notable conclusion"
            ],
            key_topics=["technology", "development", "innovation"],
            confidence_score=round(random.uniform(0.7, 0.95), 2),
            processing_time=round(random.uniform(2.0, 15.0), 2),
            created_at=datetime.utcnow(),
            **kwargs
        )
    
    # ============================================================================
    # SENTIMENT ANALYSIS DOMAIN
    # ============================================================================
    
    def create_sentiment_analysis(
        self,
        media_id: Optional[str] = None,
        **kwargs
    ) -> SentimentAnalysisResult:
        """Create a test SentimentAnalysis entity."""
        sentiments = ["positive", "negative", "neutral"]
        emotions = ["joy", "sadness", "anger", "fear", "surprise", "neutral"]
        
        return SentimentAnalysisResult(
            id=self._unique_id(),
            media_id=media_id or self._unique_id(),
            overall_sentiment=random.choice(sentiments),
            sentiment_score=round(random.uniform(-1.0, 1.0), 2),
            confidence=round(random.uniform(0.6, 0.95), 2),
            emotions={
                emotion: round(random.uniform(0.0, 1.0), 2) 
                for emotion in random.sample(emotions, 3)
            },
            sentence_sentiments=[
                {
                    "text": "This is a positive statement.",
                    "sentiment": "positive",
                    "score": 0.8
                },
                {
                    "text": "This is a neutral observation.", 
                    "sentiment": "neutral",
                    "score": 0.1
                }
            ],
            provider="transformers",
            model="distilbert-base-uncased",
            created_at=datetime.utcnow(),
            **kwargs
        )
    
    # ============================================================================
    # TOPIC MODELING DOMAIN
    # ============================================================================
    
    def create_topic_modeling(
        self,
        media_id: Optional[str] = None,
        **kwargs
    ) -> TopicModelingResult:
        """Create a test TopicModeling entity."""
        sample_topics = [
            {
                "topic_id": 0,
                "words": ["technology", "software", "development", "programming"],
                "weights": [0.3, 0.25, 0.2, 0.15],
                "coherence": 0.65
            },
            {
                "topic_id": 1, 
                "words": ["business", "market", "strategy", "growth"],
                "weights": [0.35, 0.3, 0.2, 0.1],
                "coherence": 0.72
            }
        ]
        
        return TopicModelingResult(
            id=self._unique_id(),
            media_id=media_id or self._unique_id(),
            topics=random.sample(sample_topics, random.randint(1, 2)),
            keywords=["technology", "innovation", "development", "strategy"],
            num_topics=random.randint(2, 5),
            algorithm="lda",
            coherence_score=round(random.uniform(0.4, 0.8), 2),
            perplexity=round(random.uniform(50.0, 200.0), 1),
            created_at=datetime.utcnow(),
            **kwargs
        )
    
    # ============================================================================
    # DOMAIN EVENTS DATA
    # ============================================================================
    
    def create_media_uploaded_event_data(self, **kwargs) -> Dict[str, Any]:
        """Create MediaUploaded event data."""
        return {
            "media_id": self._unique_id(),
            "user_id": self._unique_id(),
            "media_type": "AUDIO",
            "file_path": f"/uploads/test_{self._unique_id()}.mp3",
            "storage_provider": "local",
            **kwargs
        }
    
    def create_transcription_completed_event_data(self, **kwargs) -> Dict[str, Any]:
        """Create TranscriptionCompleted event data."""
        return {
            "media_id": self._unique_id(),
            "transcription_id": self._unique_id(),
            "text_content": "This is the completed transcription text.",
            **kwargs
        }
    
    # ============================================================================
    # BULK DATA CREATION
    # ============================================================================
    
    def create_multiple_users(self, count: int = 5) -> List[User]:
        """Create multiple test users."""
        return [self.create_user() for _ in range(count)]
    
    def create_multiple_media(self, count: int = 5, user_id: Optional[str] = None) -> List[Media]:
        """Create multiple test media objects."""
        return [self.create_media(user_id=user_id) for _ in range(count)]
    
    def create_complete_media_pipeline_data(self) -> Dict[str, Any]:
        """Create complete data for testing the full media processing pipeline."""
        user = self.create_user()
        media = self.create_audio_media(user_id=user.id)
        transcription = self.create_transcription(media_id=media.id)
        summary = self.create_summary(media_id=media.id)
        sentiment = self.create_sentiment_analysis(media_id=media.id)
        topics = self.create_topic_modeling(media_id=media.id)
        
        return {
            "user": user,
            "media": media,
            "transcription": transcription,
            "summary": summary,
            "sentiment_analysis": sentiment,
            "topic_modeling": topics
        }