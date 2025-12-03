# tests/utils/test_data_factory.py
"""Factory for creating realistic test data objects.
Provides consistent, valid test data for all domains.
"""
import random
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Dict, List, Optional
from uuid import uuid4

from src.shared.domain.enums import MediaStatus, MediaType
from src.media_processing.transcription.domain.transcription import (
    Transcription,
    TranscriptionStatus,
)
from src.user_management.domain.user import User, UserRole


class TestDataFactory:
    """Factory for creating test data objects with realistic values."""

    def __init__(self):
        self._counter = 0

    def _unique_id(self) -> str:
        """Generate a unique ID for test objects."""
        self._counter += 1
        return str(uuid4())

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

        extension_map = {
            MediaType.AUDIO: ".mp3",
            MediaType.VIDEO: ".mp4",
        }
        filename += extension_map.get(media_type, ".txt")

        filename_override = kwargs.pop("filename", filename)
        storage_provider = kwargs.pop("storage_provider", "local")

        return Media.create(
            user_id=user_id or self._unique_id(),
            original_file_path=f"/uploads/{filename}",
            media_type=media_type,
            storage_provider=storage_provider,
            filename=filename_override,
            file_size=random.randint(1024, 1024 * 1024),
            duration=random.randint(30, 3600) if media_type in [MediaType.AUDIO, MediaType.VIDEO] else None,
            status=status,
            media_id=kwargs.pop("media_id", None),
            **kwargs,
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

        transcription_id = kwargs.pop("id", uuid4())
        media_uuid = kwargs.pop("media_id", media_id or uuid4())

        return SimpleNamespace(
            id=transcription_id,
            media_id=media_uuid,
            text=kwargs.pop("text", random.choice(sample_texts)),
            language="en",
            provider="whisper",
            status=status,
            confidence_score=round(random.uniform(0.8, 0.99), 2),
            segments=sample_segments,
            speakers=["Speaker 1", "Speaker 2"],
            processing_time=round(random.uniform(1.0, 10.0), 2),
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