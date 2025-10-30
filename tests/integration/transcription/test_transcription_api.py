# tests/integration/transcription/test_transcription_api.py
import pytest
from httpx import AsyncClient
from uuid import uuid4

from src.auth.domain.user import User
from src.media_management.domain.enums import MediaStatus, MediaType
from src.media_management.infrastructure.orm.media_entity import MediaEntity
from src.media_processing.transcription.domain.transcription import Transcription, TranscriptionStatus

# A fixture for the async client is assumed to be available, e.g., in a root conftest.py
# If not, it should be added.

@pytest.mark.asyncio
async def test_set_speaker_aliases_success(client: AsyncClient, db_session, authenticated_user: User):
    """Tests successful update of speaker aliases via API endpoint."""
    # Arrange: Create a media and transcription record in the database
    media = MediaEntity(
        id=uuid4(),
        user_id=authenticated_user.id,
        original_file_path="/test.mp4",
        media_type=MediaType.VIDEO,
        status=MediaStatus.UPLOADED,
        storage_provider="local",
    )
    transcription = Transcription(
        id=uuid4(),
        media_id=media.id,
        status=TranscriptionStatus.COMPLETED,
        speaker_aliases={},
        result={"segments": [{"speaker": "SPEAKER_00"}]}
    )
    db_session.add(media)
    db_session.add(transcription)
    await db_session.commit()

    new_aliases = {"SPEAKER_00": "John Doe"}

    # Act: Call the API endpoint
    response = await client.put(
        f"/transcriptions/{transcription.id}/speaker-aliases",
        json={"aliases": new_aliases},
    )

    # Assert: Check the response and database state
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["speaker_aliases"] == new_aliases

    # Verify the change in the database
    updated_transcription = await db_session.get(Transcription, transcription.id)
    assert updated_transcription.speaker_aliases == new_aliases
